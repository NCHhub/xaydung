#!/usr/bin/env python3
"""
Hải Bridge — Relay server nhận task từ web, gọi Nguyễn Cao Hải và Cộng sự, trả kết quả.

Chạy trên PC:
  cd bridge && pip install fastapi uvicorn httpx && python3 server.py

Exposes qua ngrok/cloudflared:
  ngrok http 8000   → nhận URL public cho web gọi
"""
import os, json, time, uuid, subprocess, asyncio, sys
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
    allow_origins=["https://X.aladDin.vn", "http://localhost:4000"],
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
    """Trả lời qua Chorus (ChatGPT miễn phí không giới hạn), fallback proxy OpenCode."""
    # 1. Thử Chorus trước (nhanh, rẻ, không giới hạn)
    chord_res = await _call_chorus(task)
    if chord_res is not None:
        return chord_res
    # 2. Fallback proxy OpenCode (4096)
    return await _call_proxy(task)

# ===== 1. CHORUS — ChatGPT miễn phí không giới hạn =====
CHORUS_PLATFORM = os.getenv("ADVISOR_CHORUS_PLATFORM", "chatgpt")
CHORUS_ASK = os.getenv("CHORUS_ASK", f"{Path.home()}/empire/shared/tu-van-ngoai/chorus_ask.py")

async def _call_chorus(task: AdvisorTask) -> Optional[AdvisorResult]:
    """Gọi chorus_ask.py (browser automation) — return None nếu fail."""
    import re
    questions = {
        "estimate_cost": "Ước tính chi phí xây/sửa nhà",
        "audit_quote": "Soi báo giá còn thiếu hạng mục nào",
        "calculate_material": "Tính vật tư cần thiết cho công trình",
        "diagnose_issue": "Xử lý thấm/nứt nhà",
    }
    intent_hint = questions.get(task.toolIntent, "")
    prompt = (
        "Bạn là trợ lý tư vấn xây sửa nhà của Nguyễn Cao Hải và Cộng sự tại Việt Nam. "
        "Trả lời NGẮN GỌN tiếng Việt phổ thông, thân thiện, có số cụ thể (triệu/m²). "
        "Luôn lưu ý cần khảo sát thực tế. Không hứa hẹn giá chính thức.\n"
        f"Công việc: {intent_hint}.\n"
        f"Câu hỏi từ môi giới: {task.question}\n"
        "Trả lời:"
    )
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, CHORUS_ASK, prompt, "-p", CHORUS_PLATFORM,
            cwd=str(Path(CHORUS_ASK).parent),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        out = stdout.decode("utf-8", "ignore")
        if proc.returncode != 0 or ("OK" not in out and "xong" not in out):
            return None
        # Tìm đường dẫn thư mục tra-loi mới nhất từ output
        m = re.search(r'(/home/[^\s]+/tra-loi/\d{8}-\d{6})', out)
        if not m:
            return None
        answer = _read_latest_chorus(m.group(1))
        if not answer:
            return None
        return AdvisorResult(
            taskId=task.id, status="completed",
            shortAnswer=_strip_md(answer)[:1500],
            assumptions=["Tư vấn AI sơ bộ. Cần khảo sát thực tế."],
            risks=[{"level": "medium", "message": "Kết quả từ AI sơ bộ, chưa được chuyên gia kiểm duyệt."}],
            nextActions=["copy", "request_expert"],
            sources=[{"title": f"{CHORUS_PLATFORM.capitalize()} qua Nguyễn Cao Hải và Cộng sự (AI sơ bộ)", "ref": "knowledge_v0.1"}])
    except Exception:
        return None

def _read_latest_chorus(dirpath: str) -> str:
    """Đọc file tra-loi-<platform>.md mới nhất trong thư mục trả lời."""
    import glob
    for f in sorted(glob.glob(f"{dirpath}/tra-loi-{CHORUS_PLATFORM}.md")):
        text = open(f, encoding="utf-8").read()
        # Bỏ phần header meta (---...---)
        body = text.split("---", 2)
        return body[2].strip() if len(body) >= 3 else text
    return ""

# ===== 2. PROXY OpenCode (fallback) =====
async def _call_proxy(task: AdvisorTask) -> AdvisorResult:
    """Gọi OpenCode qua proxy API (port 4096) với task."""
    import re, urllib.request
    
    system = (
        "Bạn là trợ lý tư vấn xây sửa nhà của Nguyễn Cao Hải và Cộng sự. "
        "Trả lời NGẮN GỌN tiếng Việt phổ thông, thân thiện. "
        "Ước tính chi phí phải có số cụ thể (triệu/m²). "
        "Luôn lưu ý cần khảo sát thực tế. "
        "Kết thúc bằng 1 dòng JSON trên cùng 1 dòng:\n"
        '{"shortAnswer":"...","assumptions":["..."],"risks":[{"level":"low|medium|high","message":"..."}],"nextActions":["copy","request_expert"]}'
    )
    user_msg = f"{system}\n\nCâu hỏi từ môi giới:\n{task.question}"
    
    PROXY = os.getenv("ADVISOR_PROXY", "http://127.0.0.1:4096")
    
    try:
        req = urllib.request.Request(
            f"{PROXY}/session", data=b"{}",
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            session_id = json.loads(resp.read())["id"]
        
        req = urllib.request.Request(
            f"{PROXY}/session/{session_id}/message",
            data=json.dumps({"content": user_msg}).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10):
            pass
        
        start = time.time()
        answer = ""
        while time.time() - start < 90:
            await asyncio.sleep(3)
            req = urllib.request.Request(f"{PROXY}/session/{session_id}/message")
            with urllib.request.urlopen(req, timeout=10) as resp:
                messages = json.loads(resp.read())
            for m in messages:
                if m.get("info", {}).get("role") == "assistant":
                    parts = m.get("parts", [])
                    txt = "".join(p.get("text", "") for p in parts if isinstance(p, dict) and p.get("type") == "text")
                    if txt.strip():
                        answer = txt.strip()
                        break
            if answer:
                break
        
        if not answer:
            return _fallback(task.id, "Hệ thống đang xử lý chậm. Vui lòng thử lại sau hoặc nhắn Zalo 0983.601.366.")
        
        json_match = re.search(r'\{[^{}]*"shortAnswer"[^{}]*\}', answer, re.DOTALL)
        if json_match:
            try:
                d = json.loads(json_match.group())
                return AdvisorResult(
                    taskId=task.id, status="completed",
                    shortAnswer=d.get("shortAnswer", "").strip() or _strip_md(answer),
                    assumptions=d.get("assumptions", []),
                    risks=d.get("risks", []),
                    nextActions=d.get("nextActions", ["copy", "request_expert"]),
                    sources=[{"title": "Nguyễn Cao Hải và Cộng sự (AI sơ bộ)", "ref": "knowledge_v0.1"}])
            except json.JSONDecodeError:
                pass
        
        clean = _strip_md(answer)
        return AdvisorResult(
            taskId=task.id, status="completed",
            shortAnswer=clean[:1500],
            assumptions=["Đây là tư vấn sơ bộ. Cần khảo sát thực tế."],
            risks=[{"level": "medium", "message": "Kết quả từ AI sơ bộ, chưa được chuyên gia kiểm duyệt."}],
            nextActions=["copy", "request_expert"],
            sources=[{"title": "Nguyễn Cao Hải và Cộng sự (AI sơ bộ)", "ref": "knowledge_v0.1"}])
    except Exception as e:
        return _fallback(task.id, f"Lỗi hệ thống: {str(e)[:200]}")

def _strip_md(s: str) -> str:
    """Làm sạch markdown để hiển thị web gọn."""
    import re
    s = re.sub(r'#{1,6}\s*', '', s)          # heading
    s = re.sub(r'\*\*(.*?)\*\*', r'\1', s)   # bold
    s = re.sub(r'__(.*?)__', r'\1', s)       # bold alt
    s = re.sub(r'\|.*\|', '', s)             # bảng
    s = re.sub(r'-{3,}', '', s)              # hr
    s = re.sub(r'^\s*[-*]\s+', '• ', s, flags=re.MULTILINE)
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()

def _fallback(task_id, msg):
    return AdvisorResult(
        taskId=task_id, status="rejected" if "Lỗi" in msg else "needs_expert",
        shortAnswer=msg,
        risks=[{"level": "medium", "message": "Hệ thống không thể xử lý tự động."}],
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
