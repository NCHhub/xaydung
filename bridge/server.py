#!/usr/bin/env python3
"""
Hải Bridge — Relay server nhận task từ web, gọi Nguyễn Cao Hải và Cộng sự, trả kết quả.

Chạy trên PC:
  cd bridge && pip install fastapi uvicorn httpx && python3 server.py

Exposes qua ngrok/cloudflared:
  ngrok http 8000   → nhận URL public cho web gọi
"""
import os, json, time, uuid, subprocess, asyncio
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import uvicorn

# ===== CONFIG =====
PORT = int(os.getenv("BRIDGE_PORT", "8000"))
KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"
OPENCODE_BIN = os.getenv("OPENCODE_BIN", "opencode")

app = FastAPI(title="Hải Bridge", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://xaydung.aladdin.vn", "http://localhost:4000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== SCHEMAS (theo LỆNH TỔNG Mục 0.0) =====
class AdvisorTask(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    userId: Optional[str] = None
    brokerId: Optional[str] = None
    toolIntent: str = Field(..., description="answer_construction_question|estimate_cost|audit_quote|calculate_material|diagnose_issue|create_client_report")
    question: Optional[str] = None
    houseContext: Dict[str, Any] = {}
    attachmentRefs: List[str] = []
    locale: str = "vi-VN"
    createdAt: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S+07:00"))
    expiresAt: str = ""
    nonce: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])

class AdvisorResult(BaseModel):
    taskId: str
    status: str = "completed"  # completed|needs_more_input|needs_expert|rejected
    shortAnswer: str
    resultData: Optional[Dict[str, Any]] = None
    assumptions: List[str] = []
    missingInformation: List[str] = []
    risks: List[Dict[str, str]] = []
    sources: List[Dict[str, str]] = []
    nextActions: List[str] = []
    knowledgeVersion: str = "0.1.0"

# ===== KNOWLEDGE PACK =====
def load_knowledge() -> str:
    """Gộp knowledge pack từ YAML + markdown blog."""
    parts = []
    # YAML Q&A
    yaml_file = Path(__file__).parent.parent / "_data" / "moi-gioi.yml"
    if yaml_file.exists():
        parts.append(f"=== KNOWLEDGE Q&A ===\n{yaml_file.read_text(encoding='utf-8')}")
    # Blog articles
    blog_dir = Path(__file__).parent.parent / "_blog"
    if blog_dir.exists():
        for f in sorted(blog_dir.glob("*.md"))[:10]:  # limit
            parts.append(f"=== {f.stem} ===\n{f.read_text(encoding='utf-8')[:2000]}")
    return "\n\n".join(parts) if parts else "Chưa có knowledge pack. Trả lời dựa trên kiến thức chung, ghi rõ 'AI sơ bộ'."

KNOWLEDGE_CACHE = {"text": None, "ts": 0}

def get_knowledge() -> str:
    now = time.time()
    if KNOWLEDGE_CACHE["text"] is None or now - KNOWLEDGE_CACHE["ts"] > 300:
        KNOWLEDGE_CACHE["text"] = load_knowledge()
        KNOWLEDGE_CACHE["ts"] = now
    return KNOWLEDGE_CACHE["text"]

# ===== ADVISOR (gọi OpenCode CLI) =====
SYSTEM_PROMPT = """Bạn là trợ lý tư vấn xây dựng nhà ở của Nguyễn Cao Hải và Cộng sự — môi giới BĐS Hà Nội.

QUY TẮC BẮT BUỘC:
1. Trả lời NGẮN GỌN, TIẾNG VIỆT PHỔ THÔNG, học sinh lớp 5 hiểu được.
2. Luôn ghi rõ: "Đây là tư vấn sơ bộ. Cần khảo sát thực tế để có kết quả chính xác."
3. KHÔNG đưa khẳng định chắc chắn về giá, kết cấu, pháp lý.
4. Nếu câu hỏi cần chuyên gia kỹ thuật → trả lời: "Cần chuyên gia khảo sát."
5. Kết quả TRẢ VỀ JSON FORMAT:
{
  "shortAnswer": "Câu trả lời ngắn cho môi giới nói với khách",
  "assumptions": ["Giả định 1", "Giả định 2"],
  "risks": [{"level": "medium", "message": "Cần kiểm tra X"}],
  "nextActions": ["copy", "request_expert"]
}

Luôn ưu tiên tạo giá trị cho môi giới: giúp họ trả lời khách ngay, hoặc hướng dẫn đúng chuyên gia.
Không bịa số liệu, không tự tạo giá, không tự hứa."""

async def call_advisor(task: AdvisorTask) -> AdvisorResult:
    """Gọi OpenCode CLI với task và knowledge pack."""
    knowledge = get_knowledge()
    
    user_msg = f"""Câu hỏi từ môi giới:
{task.question}

Đầu vào: {json.dumps(task.houseContext, ensure_ascii=False) if task.houseContext else 'Không có'}

Kiến thức tham khảo:
{knowledge[:8000]}"""
    
    try:
        # Gọi opencode CLI (non-interactive, dùng --print hoặc qua SDK)
        result = subprocess.run(
            [OPENCODE_BIN, "--print", "--model", "ollama-cloud/gemma4:31b-cloud"],
            input=user_msg,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(Path(__file__).parent.parent),
            env={**os.environ, "OPENCODE_INSTRUCTIONS": str(Path(__file__).parent / "advisor-agents.md")}
        )
        
        raw = result.stdout.strip()
        
        # Parse JSON từ output (advisor được hướng dẫn trả JSON)
        try:
            # Tìm JSON trong output (có thể có text trước/sau)
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(raw[start:end])
                return AdvisorResult(
                    taskId=task.id,
                    status="completed",
                    shortAnswer=data.get("shortAnswer", raw[:500]),
                    assumptions=data.get("assumptions", []),
                    risks=data.get("risks", []),
                    nextActions=data.get("nextActions", ["copy", "request_expert"]),
                    sources=[{"title": "Nguyễn Cao Hải và Cộng sự (AI sơ bộ)", "ref": "knowledge_v0.1"}]
                )
        except json.JSONDecodeError:
            pass
        
        # Fallback: dùng raw text làm shortAnswer
        return AdvisorResult(
            taskId=task.id,
            status="completed",
            shortAnswer=raw[:1000] if raw else "Xin lỗi, hệ thống tạm thời không trả lời được. Vui lòng thử lại hoặc nhắn Zalo 0983.601.366.",
            assumptions=["Kết quả từ AI sơ bộ, chưa được chuyên gia kiểm duyệt"],
            risks=[{"level": "medium", "message": "Đây là tư vấn AI sơ bộ. Cần khảo sát thực tế."}],
            nextActions=["copy", "request_expert"],
            sources=[{"title": "Nguyễn Cao Hải và Cộng sự (AI sơ bộ)", "ref": "knowledge_v0.1"}]
        )
    except subprocess.TimeoutExpired:
        return AdvisorResult(
            taskId=task.id, status="needs_expert",
            shortAnswer="Hệ thống đang bận. Vui lòng thử lại sau hoặc nhắn Zalo 0983.601.366 để nhờ chuyên gia hỗ trợ.",
            risks=[{"level": "low", "message": "Timeout — hệ thống quá tải"}],
            nextActions=["request_expert"]
        )
    except FileNotFoundError:
        return AdvisorResult(
            taskId=task.id, status="rejected",
            shortAnswer="OpenCode chưa được cài trên hệ thống. Liên hệ quản trị.",
            risks=[{"level": "high", "message": "OpenCode binary not found"}],
            nextActions=["request_expert"]
        )
    except Exception as e:
        return AdvisorResult(
            taskId=task.id, status="rejected",
            shortAnswer=f"Lỗi hệ thống: {str(e)[:200]}",
            risks=[{"level": "high", "message": str(e)[:200]}],
            nextActions=["request_expert"]
        )

# ===== ENDPOINTS =====
@app.get("/health")
async def health():
    return {"healthy": True, "version": "0.1.0", "uptime": time.time() - START_TIME}

@app.post("/task", response_model=AdvisorResult)
async def create_task(task: AdvisorTask):
    """Nhận task từ web → gọi Advisor → trả kết quả."""
    if not task.question or len(task.question.strip()) < 5:
        raise HTTPException(400, "Câu hỏi quá ngắn. Vui lòng nhập chi tiết hơn.")
    if len(task.question) > 2000:
        raise HTTPException(400, "Câu hỏi quá dài. Vui lòng rút gọn.")
    
    result = await call_advisor(task)
    return result

@app.get("/capabilities")
async def list_capabilities():
    """Liệt kê các capability hiện có (cho web hiển thị nút)."""
    return {
        "capabilities": [
            {"id": "answer_construction_question", "title": "Khách đang hỏi gì?", "icon": "🗣️", "description": "Trả lời câu hỏi xây/sửa nhà cho môi giới gửi khách"},
            {"id": "estimate_cost", "title": "Ước tính chi phí", "icon": "💰", "description": "Ước tính sơ bộ chi phí xây/sửa theo thông số"},
            {"id": "audit_quote", "title": "Soi báo giá", "icon": "🔍", "description": "Kiểm tra báo giá còn thiếu hạng mục nào"},
            {"id": "calculate_material", "title": "Tính vật tư", "icon": "🧮", "description": "Tính số lượng vật tư cần thiết"},
        ]
    }

# ===== MAIN =====
START_TIME = time.time()

if __name__ == "__main__":
    print(f"🏗️  Hải Bridge starting on port {PORT}...")
    print(f"   Health: http://localhost:{PORT}/health")
    print(f"   Task:   http://localhost:{PORT}/task")
    print(f"   Capabilities: http://localhost:{PORT}/capabilities")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
