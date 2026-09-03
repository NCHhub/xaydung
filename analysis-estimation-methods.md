# Phân Tích & Đề Xuất Đa Phương Pháp Ước Tính Chi Phí Xây Dựng

> **Bối cảnh**: X.aladDin.vn — công cụ trợ lý môi giới thi công xây dựng  
> **Yêu cầu Diamond (21 năm KN)**: "Phải ước tính bằng nhiều phương pháp rồi tổng hợp lại để giảm thiểu sai số"

---

## 1. DỮ LIỆU HIỆN CÓ (Tổng Hợp)

| Hạng mục | Phạm vi | Ghi chú |
|----------|---------|---------|
| **Xây mới Hà Nội** | 15tr/m² sàn (phổ thông) × 1.2 (khá) × 1.5 (cao cấp) | Đơn giá cơ sở |
| **Hệ số cấu trúc** | Mái tôn 0.85, Bê tông 1.10, Thái 1.25 | Nhân vào đơn giá cơ sở |
| **Hệ số móng** | Băng 1.0, Đơn giản 0.85, Cọc 1.25 | Nhân vào đơn giá cơ sở |
| **Sửa chữa** | Nhẹ 2.5tr/m², Vừa 5tr/m², Lớn 9tr/m² | Theo m² sàn |
| **Dự phòng** | 12% (xây mới), 25% (sửa cũ) | % giá trị thi công |
| **Thiết kế KTS** | 200k–450k/m² sàn | Phổ thông → Cao cấp |
| **Xin phép** | 15tr–100tr | Tùy loại giấy phép |
| **Giám sát** | 3–8% giá trị TH | % giá trị thi công |
| **Nội thất** | 2tr–8tr/m² sàn | Phổ thông → Cao cấp |
| **Phá dỡ** | 30tr–50tr | Gói trọn |
| **Hạ tầng** | 30tr–50tr | Điện/nước/kết nối |

---

## 2. 5 PHƯƠNG PHÁP ƯỚC TÍNH PHỔ BIẾN TẠI VN

| # | Phương pháp | Tên VN | Tên EN | Cốt lõi |
|---|-------------|--------|--------|---------|
| 1 | **Đơn giá/m² sàn** | Đơn giá sàn | Unit Rate per m² | Đơn giá cơ sở × hệ số × diện tích |
| 2 | **Phân tích tỷ trọng** | Tỷ trọng hạng mục | Elemental Cost Analysis | Chia %: Thô / Hoàn thiện / M&E / Thiết kế / Phép / Dự phòng |
| 3 | **So sánh benchmark** | Công trình tương tự | Comparative / Benchmarking | Tra cứu DB công trình đã thi công gần nhất |
| 4 | **Bottom-up (BOQ)** | Phân tích từng hạng mục | Bottom-up / Bill of Quantities | Vật tư + Nhân công + Máy thi công từng hạng mục |
| 5 | **Parametric / Regression** | Tham số / Hồi quy | Parametric Estimation | Mô hình toán: Chi phí = f(diện tích, tầng, cấu trúc, vị trí, v.v.) |

---

## 3. ĐỐI CHIẾU ƯU / NHƯỢC MỖI PHƯƠNG PHÁP

| Tiêu chí | 1. Đơn giá/m² | 2. Tỷ trọng | 3. Benchmark | 4. Bottom-up (BOQ) | 5. Parametric |
|----------|---------------|-------------|--------------|--------------------|---------------|
| **Độ chính xác** | ±25–35% | ±15–25% | ±20–30% | ±5–15% | ±10–20% |
| **Dữ liệu đầu vào** | Diện tích, loại hình, cấp độ | Diện tích + % tỷ trọng chuẩn | DB ≥20 công trình tương tự | Bản vẽ KTS + CTKT + vật liệu | Dữ liệu lịch sử đa biến |
| **Thời gian tính** | <1 giây (client) | <1 giây (client) | 1–5 giây (cần DB) | 30–120 phút (cần BOQ) | <1 giây (model trained) |
| **Khi nào dùng** | Giai đoạn ý tưởng, khái quát | Giai đoạn tiền thiết kế | Có DB công trình gần | Có bản vẽ kỹ thuật chi tiết | Đã có ≥100 mẫu train |
| **Sai số phổ biến** | Bỏ qua: phép, thiết kế, GTGT, lạm phát, rủi ro địa chất | Tỷ trọng cố định ≠ thực tế từng dự án | Công trình tham chiếu khác vị trí/thời gian | Sai số đo lượng, giá vật liệu biến động | Overfitting, thiếu biến môi trường |
| **Chi phí triển khai** | 0 (đã có) | Thấp (logic % cố định) | Trung (cần crawl DB) | Cao (cần BOQ tool, vật liệu API) | Cao (ML pipeline, retrain) |

---

## 4. ĐỀ XUẤT CÁCH TỔNG HỢP (ENSEMBLE)

### 4.1 Triết lý: Không lấy trung bình đơn thuần — lấy **khoảng tin cậy (Confidence Interval)**

> **Sai số giảm khi nhiều phương pháp độc lập hội tụ** (Wisdom of Crowds). Nếu 3 phương pháp cho 520, 590, 680 → khoảng 520–680 tr có ý nghĩa hơn bất kỳ số đơn lẻ nào.

### 4.2 Ma trận trọng số đề xuất (adaptive theo giai đoạn dự án)

| Giai đoạn | Phương pháp 1 (m²) | Phương pháp 2 (Tỷ trọng) | Phương pháp 3 (Benchmark) | Phương pháp 4 (BOQ) | Phương pháp 5 (Parametric) |
|-----------|---------------------|--------------------------|---------------------------|---------------------|----------------------------|
| **Ý tưởng / Khảo sát** | 0.40 | 0.30 | 0.20 | 0.00 | 0.10 |
| **Tiền thiết kế** | 0.25 | 0.35 | 0.25 | 0.00 | 0.15 |
| **Kỹ thuật / Xin phép** | 0.15 | 0.30 | 0.20 | 0.25 | 0.10 |
| **Chuẩn bị thi công** | 0.10 | 0.20 | 0.10 | 0.50 | 0.10 |

> **Trọng số điều chỉnh động**: Nếu có bản vẽ KTS → tăng BOQ. Nếu có DB benchmark tốt → tăng Benchmark. Nếu chỉ có diện tích → lệch về m² + Tỷ trọng.

### 4.3 Công thức tính ensemble

```python
# Pseudocode
estimates = {
    "unit_rate": calc_unit_rate(area, type, grade, struct_coef, foundation_coef),
    "elemental": calc_elemental(area, type, grade),  # % thô/hoàn thiện/MEP/...
    "benchmark": query_benchmark_db(area, location, type, grade),  # median ± IQR
    "boq": calc_boq(drawings) if drawings else None,
    "parametric": ml_predict(features) if model_ready else None
}

# Loại None
valid = {k:v for k,v in estimates.items() if v is not None}

# Weighted median (robust hơn mean)
weights = get_weights(project_stage)
weighted_values = []
for method, value in valid.items():
    weighted_values.extend([value] * int(weights[method] * 100))

# Kết quả
median_est = median(weighted_values)
p10, p90 = percentile(weighted_values, 10), percentile(weighted_values, 90)

output = f"Ước tính: {p10:,.0f}–{p90:,.0f} triệu (median: {median_est:,.0f} triệu)"
detail = ", ".join([f"{k}: {v:,.0f}tr" for k,v in valid.items()])
```

### 4.4 Format output đề xuất trên UI

```
┌─────────────────────────────────────────────────────────────┐
│  ƯỚC TÍNH CHI PHÍ TỔNG HỢP                                  │
├─────────────────────────────────────────────────────────────┤
│  Khoảng tin cậy 80%:  520 – 780 triệu VNĐ                   │
│  Giá trị trung vị:    640 triệu VNĐ                         │
├─────────────────────────────────────────────────────────────┤
│  Chi tiết từng phương pháp:                                 │
│  • Đơn giá/m² sàn:        580 triệu                         │
│  • Tỷ trọng hạng mục:     620 triệu                         │
│  • Benchmark (3 CT gần):  650 triệu                         │
│  • Bottom-up (BOQ):       710 triệu   ← có bản vẽ           │
│  • Parametric (ML):       590 triệu                         │
├─────────────────────────────────────────────────────────────┤
│  ⚠️ Lưu ý: Sai số thực tế ±15–20%. Chưa bao gồm: GTGT 10%, │
│  lạm phát năm thi công, rủi ro địa chất, thay đổi thiết kế. │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. ĐỀ XUẤT TRIỂN KHAI TRÊN WEB (X.aladDin.vn)

### 5.1 Phân loại Client-side vs Server-side

| Phương pháp | Chạy client-side (JS) | Cần Server/AI | Lý do |
|-------------|----------------------|---------------|-------|
| **1. Đơn giá/m²** | ✅ **Đã có** | ❌ | Toán học đơn thuần, 0 token |
| **2. Tỷ trọng** | ✅ **Dễ thêm** | ❌ | Chỉ cần bảng % cố định + logic nhân |
| **3. Benchmark** | ❌ | ✅ **Cần API/DB** | Cần DB ≥200 công trình, search fuzzy |
| **4. Bottom-up** | ❌ | ✅ **Cần BOQ Engine** | Cần parse bản vẽ, giá vật liệu real-time |
| **5. Parametric** | ❌ | ✅ **Cần ML Model** | Cần model trained, feature engineering |

### 5.2 Roadmap triển khai (3 phase)

| Phase | Mục tiêu | Phương pháp kích hoạt | Công nghệ | Thời gian |
|-------|----------|----------------------|-----------|-----------|
| **Phase 1 (Tuần 1-2)** | Ensemble client-side cơ bản | 1 + 2 | React + TypeScript, 0 backend | 2 tuần |
| **Phase 2 (Tuần 3-6)** | Benchmark API + Cache | 1 + 2 + 3 | Supabase/PostgreSQL + Edge Function | 4 tuần |
| **Phase 3 (Tuần 7-12)** | BOQ Lite + Parametric MVP | 1-5 (full) | Python/FastAPI + ONNX model + vector DB | 6 tuần |

### 5.3 Phase 1: Client-side Ensemble (Có thể làm ngay hôm nay)

**Input component mở rộng:**
```tsx
// Thêm vào form hiện tại
interface ExtendedInput {
  // Hiện có
  area: number;           // m² sàn
  type: 'new' | 'renovate';
  grade: 'basic' | 'standard' | 'premium';
  structure: 'steel' | 'concrete' | 'thai';
  foundation: 'strip' | 'simple' | 'pile';
  
  // Mới bổ sung
  floors: number;              // Số tầng
  hasDesign: boolean;          // Đã có bản vẽ KTS?
  designTier: 'basic' | 'standard' | 'premium';
  needPermit: boolean;         // Cần xin phép?
  permitType: 'simple' | 'full';
  needSupervision: boolean;    // Có giám sát?
  supervisionTier: 'basic' | 'full';
  fitoutTier: 'none' | 'basic' | 'standard' | 'premium';
  hasDemolition: boolean;      // Có phá dỡ?
  infraScope: 'none' | 'basic' | 'full';
  location: 'hanoi' | 'hcmc' | 'other'; // để benchmark
}
```

**Logic tính client-side (Pure TS, 0 token):**

```typescript
// /src/lib/estimation/ensemble-client.ts

const ELEMENTAL_RATIOS = {
  new: {
    basic:     { shell: 0.45, finishing: 0.30, mep: 0.15, design: 0.03, permit: 0.02, contingency: 0.12 },
    standard:  { shell: 0.42, finishing: 0.33, mep: 0.15, design: 0.03, permit: 0.02, contingency: 0.12 },
    premium:   { shell: 0.38, finishing: 0.38, mep: 0.15, design: 0.04, permit: 0.02, contingency: 0.12 },
  },
  renovate: {
    light:     { shell: 0.30, finishing: 0.40, mep: 0.15, design: 0.05, permit: 0.00, contingency: 0.25 },
    medium:    { shell: 0.35, finishing: 0.35, mep: 0.15, design: 0.05, permit: 0.00, contingency: 0.25 },
    heavy:     { shell: 0.40, finishing: 0.30, mep: 0.15, design: 0.05, permit: 0.00, contingency: 0.25 },
  }
};

const FIXED_COSTS = {
  design: { basic: 200, standard: 325, premium: 450 },      // k VNĐ/m²
  permit: { simple: 15, full: 100 },                         // triệu VNĐ
  supervision: { basic: 0.03, full: 0.08 },                  // % construction value
  fitout: { none: 0, basic: 2, standard: 5, premium: 8 },    // triệu/m²
  demolition: 40,                                            // triệu (mid)
  infrastructure: 40,                                        // triệu (mid)
};

function estimateUnitRate(input: ExtendedInput): number {
  // Logic hiện tại của X.aladDin.vn
  let base = 15; // tr/m²
  if (input.grade === 'standard') base *= 1.2;
  if (input.grade === 'premium') base *= 1.5;
  if (input.structure === 'concrete') base *= 1.10;
  if (input.structure === 'thai') base *= 1.25;
  if (input.foundation === 'simple') base *= 0.85;
  if (input.foundation === 'pile') base *= 1.25;
  return base * input.area;
}

function estimateElemental(input: ExtendedInput): number {
  const ratios = input.type === 'new' 
    ? ELEMENTAL_RATIOS.new[input.grade]
    : ELEMENTAL_RATIOS.renovate[input.grade === 'basic' ? 'light' : input.grade === 'standard' ? 'medium' : 'heavy'];
  
  const construction = estimateUnitRate(input);
  let total = construction;
  
  // Thiết kế
  total += FIXED_COSTS.design[input.designTier] * input.area / 1000; // tr
  
  // Phép
  if (input.needPermit) total += FIXED_COSTS.permit[input.permitType];
  
  // Giám sát
  if (input.needSupervision) total += construction * FIXED_COSTS.supervision[input.supervisionTier];
  
  // Nội thất
  total += FIXED_COSTS.fitout[input.fitoutTier] * input.area;
  
  // Phá dỡ
  if (input.hasDemolition) total += FIXED_COSTS.demolition;
  
  // Hạ tầng
  if (input.infraScope !== 'none') total += FIXED_COSTS.infrastructure;
  
  // Dự phòng (đã có trong ratios nhưng tính riêng cho các chi phí thêm)
  const extraCosts = total - construction;
  total += extraCosts * ratios.contingency;
  
  return total;
}

function ensembleClient(input: ExtendedInput): EnsembleResult {
  const method1 = estimateUnitRate(input);
  const method2 = estimateElemental(input);
  // Method 3,4,5 = null ở client
  
  const valid = { "Đơn giá/m²": method1, "Tỷ trọng hạng mục": method2 };
  const values = Object.values(valid);
  
  // Weighted median với trọng số phase 1
  const weights = { "Đơn giá/m²": 0.4, "Tỷ trọng hạng mục": 0.6 };
  const weighted = [];
  for (const [method, val] of Object.entries(valid)) {
    const count = Math.round(weights[method] * 100);
    for (let i = 0; i < count; i++) weighted.push(val);
  }
  weighted.sort((a,b) => a-b);
  
  const median = weighted[Math.floor(weighted.length/2)];
  const p10 = weighted[Math.floor(weighted.length * 0.1)];
  const p90 = weighted[Math.floor(weighted.length * 0.9)];
  
  return {
    range: { min: p10, max: p90, median },
    breakdown: valid,
    confidence: 0.65, // Chỉ 2 phương pháp
    methodsUsed: Object.keys(valid),
    note: "Chưa có benchmark/BOQ/ML. Sai số ước lượng ±25-30%."
  };
}
```

---

## 6. KẾT LUẬN & HÀNH ĐỘNG NGAY

| Hành động | Ưu tiên | Người làm | Thời gian |
|-----------|---------|-----------|-----------|
| **1. Mở rộng form input** (thêm 10 field mới) | 🔴 CAO | @coder | 2h |
| **2. Viết `ensemble-client.ts`** logic 2 phương pháp | 🔴 CAO | @coder | 3h |
| **3. Cập nhật UI hiển thị range + breakdown** | 🔴 CAO | @coder | 2h |
| **4. Test với 5 case thực tế Diamond cho** | 🟡 TRUNG BÌNH | @reasoner + Diamond | 1h |
| **5. Thiết kế schema Benchmark DB** (phase 2) | 🟢 THẤP | @architect | 1 ngày |

---

## 7. GHI CHÚ QUAN TRỌNG TỪ DIAMOND

> **"Khách hàng môi giới chỉ cần khoảng tin cậy để báo giá nhanh. Không cần chính xác 100% — cần *ít sai* hơn đối thủ. Hiện tại đối thủ chỉ báo 1 con số. Chúng ta báo *khoảng* + *giải thích sai số* → khác biệt cạnh tranh."**

> **"Phase 1 làm xong ngay hôm nay. Phase 2 crawl data từ các trang thầu, sàn BĐS, hồ sơ công trình công khai. Phase 3 sau khi có ≥200 mẫu train parametric."**

---

*Tài liệu tạo bởi @reasoner — Reasoning Specialist*  
*Phiên bản: 1.0 | Ngày: 2026-09-03*