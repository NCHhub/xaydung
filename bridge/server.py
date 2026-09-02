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
# Mỗi người dùng (userId) = 1 hội thoại riêng (Chorus session) để LIỀN MẠCH + CÓ BỘ NHỚ.
# Prompt LUÔN gắn knowledge pack + persona Hải (trí tuệ của chúng ta).
CHORUS_API = os.getenv("CHORUS_API", "http://127.0.0.1:4747")
CHORUS_PLATFORM = os.getenv("ADVISOR_CHORUS_PLATFORM", "chatgpt")

# Conversation store: userId -> {"sid": <chorus session id>, "updated": ts}
CONV_DIR = Path(__file__).parent / "conversations"
CONV_FILE = CONV_DIR / "conversations.json"
CONV_LOCK = asyncio.Lock()

def _conv_load() -> Dict[str, Dict[str, Any]]:
    try:
        return json.loads(CONV_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _conv_save(data: Dict[str, Dict[str, Any]]):
    CONV_DIR.mkdir(parents=True, exist_ok=True)
    CONV_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def _user_key(task: AdvisorTask) -> str:
    """userId > brokerId > 'anonymous'. Dấu vết người dùng để giữ hội thoại riêng."""
    return task.userId or task.brokerId or "anonymous"

def _build_system_prompt() -> str:
    """Prompt nền = trí tuệ + dữ liệu của chúng ta (persona Hải + knowledge pack)."""
    return (
        "BẠN LÀ: 'Nguyễn Cao Hải và Cộng sự' — trợ lý tư vấn xây/sửa nhà cho môi giới BĐS Việt Nam. "
        "Bạn giúp môi giới trả lời khách, ước tính chi phí, soi báo giá, tính vật tư, xử lý thấm/nứt.\n\n"
        "PHONG CÁCH HẢI: ngắn gọn, tiếng Việt phổ thông lớp 5 hiểu được, thân thiện, thực tế, "
        "không bịa số, không hứa giá chính thức, luôn nhắc cần khảo sát thực tế.\n\n"
        "DỮ LIỆU + TRÍ TUỆ CỦA CHÚNG TA (knowledge pack) — dùng làm nền, ưu tiên hơn kiến thức chung:\n"
        f"{get_knowledge()[:8000]}\n\n"
        "NHIỆM VỤ: trả lời câu hỏi của môi giới sao cho họ có thể gửi khách ngay. "
        "Có số cụ thể (triệu/m²) khi ước tính. Luôn ghi chú cần khảo sát thực tế."
    )

# HTTP helper đồng bộ (chạy trong thread pool)
def _chorus_http(method: str, path: str, payload: dict | None = None, timeout: int = 90) -> dict:
    import urllib.request
    req = urllib.request.Request(
        f"{CHORUS_API}{path}",
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Content-Type": "application/json"} if payload is not None else {},
        method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())

def _get_chorus_answer(sid: str, max_wait: int = 90) -> str:
    """Poll session cho tới khi complete, trả về response của platform đích."""
    import time as _t
    deadline = _t.time() + max_wait
    while _t.time() < deadline:
        data = _chorus_http("GET", f"/api/sessions/{sid}", timeout=15)
        if data.get("status") == "complete":
            resp = data.get("responses", {}).get(CHORUS_PLATFORM)
            if isinstance(resp, dict) and resp.get("error"):
                return ""
            return str(resp) if resp and "[No response" not in str(resp) else ""
        _t.sleep(3)
    return ""

async def _call_chorus(task: AdvisorTask) -> Optional[AdvisorResult]:
    """Duy trì 1 hội thoại Chorus riêng theo userId; follow-up để giữ bộ nhớ."""
    import functools
    async with CONV_LOCK:
        convs = _conv_load()
        key = _user_key(task)
        conv = convs.get(key, {})
        sid = conv.get("sid")
    
    try:
        system_prompt = _build_system_prompt()
        user_q = f"{system_prompt}\n\n===== CÂU HỎI MỚI TỪ MÔI GIỚI =====\n{task.question}"
        
        if sid:
            # Đã có hội thoại → follow-up (ChatGPT nhớ bối cảnh, liền mạch)
            await asyncio.to_thread(
                _chorus_http, "POST", f"/api/sessions/{sid}/followup",
                {"prompt": user_q}, 120)
        else:
            # Lần đầu → tạo hội thoại riêng cho người dùng
            sess = await asyncio.to_thread(
                _chorus_http, "POST", "/api/query",
                {"prompt": user_q, "platforms": [CHORUS_PLATFORM]}, 120)
            sid = sess.get("session_id")
            if not sid:
                return None
            async with CONV_LOCK:
                convs = _conv_load()
                convs[key] = {"sid": sid, "updated": time.time()}
                _conv_save(convs)
        
        # Poll kết quả
        answer = await asyncio.to_thread(_get_chorus_answer, sid, 90)
        if not answer:
            return None
        return AdvisorResult(
            taskId=task.id, status="completed",
            shortAnswer=_strip_md(answer)[:1800],
            assumptions=["Tư vấn AI sơ bộ dựa trên knowledge pack. Cần khảo sát thực tế."],
            risks=[{"level": "medium", "message": "Kết quả từ AI sơ bộ, chưa được chuyên gia kiểm duyệt."}],
            nextActions=["copy", "request_expert"],
            sources=[{"title": f"{CHORUS_PLATFORM.capitalize()} qua Nguyễn Cao Hải và Cộng sự (AI sơ bộ)", "ref": "knowledge_v0.1"}])
    except Exception as e:
        print(f"[chorus] error: {e}", flush=True)
        return None

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
