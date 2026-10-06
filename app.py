import io
import os
import time
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="Hệ Thống Theo Dõi Kỷ Luật Lớp Học",
    layout="wide",
    page_icon="📋",
)

# --------------------------------------------------------------------------
# DÁN LINK GOOGLE APPS SCRIPT KẾT THÚC BẰNG /exec VÀO GIỮA NGOẶC KÉP:
API_URL = "https://script.google.com/macros/s/AKfycbyni3dkog7q0KindO9_2cdK3A036eoESJHVDLOhomp5qTcEqJY1qXiia7RXeyHoc8M/exec"
# --------------------------------------------------------------------------

DATA_FILE = "du_lieu_thi_dua.csv"

# Chỉ giữ duy nhất lỗi Nói chuyện trong giờ học (mặc định -2 điểm/lần)
DANH_SACH_LOI = {
    "🗣️ Nói chuyện trong giờ học (-2 điểm)": -2,
}

DEFAULT_STUDENTS = [
    {
        "STT": 1,
        "Họ và tên": "Võ Huỳnh Minh An",
        "Tổ": "Tổ 1",
        "Điểm thi đua": 100,
        "Xếp loại": "Tốt",
        "Lỗi vi phạm": "None",
    },
    {
        "STT": 2,
        "Họ và tên": "Huỳnh Bảo Ngọc Thiên Ân",
        "Tổ": "Tổ 1",
        "Điểm thi đua": 100,
        "Xếp loại": "Tốt",
        "Lỗi vi phạm": "None",
    },
    {
        "STT": 3,
        "Họ và tên": "Trần Quốc Bảo",
        "Tổ": "Tổ 2",
        "Điểm thi đua": 100,
        "Xếp loại": "Tốt",
        "Lỗi vi phạm": "None",
    },
]


def tinh_xep_loai(diem):
    try:
        diem = float(diem)
    except Exception:
        diem = 100.0
    if diem >= 100:
        return "Tốt"
    elif diem >= 85:
        return "Khá"
    elif diem >= 75:
        return "Trung bình"
    else:
        return "Yếu"


def clean_dataframe(df_input):
    if df_input is None or df_input.empty:
        return pd.DataFrame(DEFAULT_STUDENTS)

    required_cols = ["STT", "Họ và tên", "Tổ", "Điểm thi đua", "Xếp loại", "Lỗi vi phạm"]
    for col in required_cols:
        if col not in df_input.columns:
            df_input[col] = ""

    df_clean = df_input.dropna(subset=["Họ và tên"]).copy()
    df_clean["Họ và tên"] = df_clean["Họ và tên"].astype(str).str.strip()
    df_clean = df_clean[~df_clean["Họ và tên"].str.lower().isin(["nan", "none", ""])]

    df_clean["Tổ"] = df_clean["Tổ"].fillna("Tổ 1").astype(str).str.strip()
    df_clean["Điểm thi đua"] = (
        pd.to_numeric(df_clean["Điểm thi đua"], errors="coerce").fillna(100).astype(int)
    )
    df_clean["Xếp loại"] = df_clean["Điểm thi đua"].apply(tinh_xep_loai)
    df_clean["Lỗi vi phạm"] = df_clean["Lỗi vi phạm"].fillna("None").astype(str)

    return df_clean.reset_index(drop=True)


def load_data():
    if API_URL and "/exec" in API_URL:
        try:
            res = requests.get(API_URL, params={"_t": time.time()}, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if isinstance(data, list) and len(data) > 1:
                    df_temp = pd.DataFrame(data[1:], columns=data[0])
                    df_temp = clean_dataframe(df_temp)
                    df_temp.to_csv(DATA_FILE, index=False)
                    return df_temp
        except Exception:
            pass

    if os.path.exists(DATA_FILE):
        try:
            return clean_dataframe(pd.read_csv(DATA_FILE))
        except Exception:
            pass

    return pd.DataFrame(DEFAULT_STUDENTS)


def update_gsheet(name, score, xeploai, log_text):
    if not API_URL or "/exec" not in API_URL:
        return False, "Chưa điền link API_URL chuẩn"

    try:
        params = {
            "action": "update",
            "name": name,
            "score": score,
            "xeploai": xeploai,
            "log": log_text,
            "_t": time.time(),
        }
        res = requests.get(API_URL, params=params, timeout=12)
        if res.status_code == 200:
            res_json = res.json()
            if res_json.get("status") == "success":
                return True, "Thành công"
            return False, res_json.get("message", "Lỗi từ Apps Script")
        return False, f"Lỗi HTTP: {res.status_code}"
    except Exception as e:
        return False, str(e)


def reset_new_week_gsheet():
    if not API_URL or "/exec" not in API_URL:
        return False, "Chưa điền link API_URL chuẩn"

    try:
        params = {"action": "reset_week", "_t": time.time()}
        res = requests.get(API_URL, params=params, timeout=15)
        if res.status_code == 200:
            res_json = res.json()
            if res_json.get("status") == "success":
                return True, "Thành công"
            return False, res_json.get("message", "Lỗi reset từ Apps Script")
        return False, f"Lỗi kết nối HTTP: {res.status_code}"
    except Exception as e:
        return False, str(e)


# Khởi tạo dữ liệu
if "df" not in st.session_state:
    st.session_state.df = load_data()

df = st.session_state.df

# ====================================================
# SIDEBAR
# ====================================================
with st.sidebar:
    st.header("🔐 ĐĂNG NHẬP VAI TRÒ")
    vai_tro = st.selectbox(
        "Bạn là ai?:",
        [
            "👑 Giáo viên chủ nhiệm",
            "Tổ trưởng Tổ 1",
            "Tổ trưởng Tổ 2",
            "Tổ trưởng Tổ 3",
            "Tổ trưởng Tổ 4",
        ],
    )

    st.markdown("---")
    st.subheader("📁 Tải danh sách lớp mới")
    uploaded_file = st.file_uploader(
        "Chọn file Excel (.xlsx) hoặc CSV:",
        type=["xlsx", "csv"],
        help="Cột cần có: STT, Họ và tên, Tổ",
    )

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".xlsx"):
                new_df = pd.read_excel(uploaded_file)
            else:
                new_df = pd.read_csv(uploaded_file)

            new_df = clean_dataframe(new_df)
            st.session_state.df = new_df
            new_df.to_csv(DATA_FILE, index=False)
            st.success("✅ Đã nạp danh sách lớp thành công!")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Lỗi đọc file: {e}")

    st.markdown("---")
    st.subheader("Chức năng:")

    danh_sach_menu = [
        "📝 Ghi Nhận Lỗi Vi Phạm",
        "📊 Bảng Tổng Hợp Lớp",
        "📬 Tải File Báo Cáo",
    ]
    if "Giáo viên" in vai_tro:
        danh_sach_menu.append("⚙️ Quản Lý Tuần Mới (Reset)")

    chuc_nang = st.radio("Lựa chọn màn hình:", danh_sach_menu, label_visibility="collapsed")

    st.markdown("---")
    if st.button("🔄 Cập nhật dữ liệu mới nhất", use_container_width=True):
        st.session_state.df = load_data()
        st.rerun()

# ====================================================
# MAIN VIEW
# ====================================================

if "Tổ 1" in vai_tro:
    df_role = df[df["Tổ"].astype(str).str.contains("1", na=False)].copy()
elif "Tổ 2" in vai_tro:
    df_role = df[df["Tổ"].astype(str).str.contains("2", na=False)].copy()
elif "Tổ 3" in vai_tro:
    df_role = df[df["Tổ"].astype(str).str.contains("3", na=False)].copy()
elif "Tổ 4" in vai_tro:
    df_role = df[df["Tổ"].astype(str).str.contains("4", na=False)].copy()
else:
    df_role = df.copy()

if chuc_nang == "📝 Ghi Nhận Lỗi Vi Phạm":
    st.title(f"{vai_tro}")

    list_to = ["Tất cả các bạn"] + sorted(list(df_role["Tổ"].dropna().unique()))
    col_filter, _ = st.columns([2, 2])
    with col_filter:
        to_duoc_chon = st.selectbox("👉 Lọc theo Tổ:", list_to)

    if to_duoc_chon != "Tất cả các bạn":
        df_form = df_role[df_role["Tổ"] == to_duoc_chon].copy()
    else:
        df_form = df_role.copy()

    with st.form("form_nhap_diem"):
        valid_students = df_form[df_form["Họ và tên"].str.strip() != ""]
        if not valid_students.empty:
            ds_lua_chon_hs = [
                f"{row['Họ và tên']} ({row['Tổ']})"
                for _, row in valid_students.iterrows()
            ]
        else:
            ds_lua_chon_hs = ["(Chưa có học sinh nào)"]

        c1, c2 = st.columns([2, 1])
        with c1:
            hs_chon = st.selectbox("👤 Chọn học sinh vi phạm:", ds_lua_chon_hs)
            loi_chon = st.selectbox("📋 Hành vi vi phạm:", list(DANH_SACH_LOI.keys()))
        with c2:
            so_lan = st.number_input("🔢 Số lần nhắc nhở / vi phạm:", min_value=1, max_value=10, value=1)
            ghi_chu = st.text_input("✏️ Ghi chú (Tiết/Môn...):")

        btn_save = st.form_submit_button("💾 LƯU VI PHẠM")

        if btn_save:
            if hs_chon == "(Chưa có học sinh nào)":
                st.error("⚠️ Vui lòng chọn học sinh hợp lệ!")
            else:
                ten_hs_thuc_te = hs_chon.split(" (")[0].strip()
                match_indices = df[df["Họ và tên"] == ten_hs_thuc_te].index

                if len(match_indices) > 0:
                    idx = match_indices[0]
                    diem_thay_doi = int(DANH_SACH_LOI[loi_chon]) * int(so_lan)
                    curr_score = int(df.at[idx, "Điểm thi đua"])
                    new_score = curr_score + diem_thay_doi
                    xeploai_moi = tinh_xep_loai(new_score)

                    noi_dung_loi = loi_chon.split(" (")[0]
                    log_text = f"{noi_dung_loi} x{so_lan}" + (f" ({ghi_chu})" if ghi_chu else "")
                    old_log = str(df.at[idx, "Lỗi vi phạm"]).strip()

                    if old_log in ["None", "nan", "", "NaN"]:
                        full_log = log_text
                    else:
                        full_log = f"{old_log} | {log_text}"

                    df.at[idx, "Điểm thi đua"] = new_score
                    df.at[idx, "Xếp loại"] = xeploai_moi
                    df.at[idx, "Lỗi vi phạm"] = full_log
                    df.to_csv(DATA_FILE, index=False)

                    if API_URL and "/exec" in API_URL:
                        with st.spinner("Đang đồng bộ lên Google Sheets..."):
                            ok, msg = update_gsheet(ten_hs_thuc_te, new_score, xeploai_moi, full_log)
                            if not ok:
                                st.warning(f"Lưu nội bộ thành công, chưa đồng bộ lên mạng: {msg}")

                    st.success(f"✅ Đã ghi nhận vi phạm cho học sinh {ten_hs_thuc_te}!")
                    time.sleep(1)
                    st.rerun()

    st.markdown("---")
    st.subheader("📋 Bảng theo dõi học sinh:")
    st.dataframe(df_form, use_container_width=True, hide_index=True)

elif chuc_nang == "📊 Bảng Tổng Hợp Lớp":
    st.title("📊 BẢNG TỔNG HỢP TOÀN LỚP")
    st.dataframe(df, use_container_width=True, hide_index=True)

elif chuc_nang == "📬 Tải File Báo Cáo":
    st.title("📬 TẢI FILE BÁO CÁO")
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="ViPham")
    buffer.seek(0)
    st.download_button(
        label="📥 Tải xuống file Excel (.xlsx)",
        data=buffer,
        file_name="Bao_Cao_Vi_Pham.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

elif chuc_nang == "⚙️ Quản Lý Tuần Mới (Reset)":
    st.title("⚙️ QUẢN LÝ VÀ CHUYỂN SANG TUẦN MỚI")
    st.warning("⚠️ **LƯU Ý:** Tải file Excel báo cáo trước khi thực hiện reset!")

    confirm_check = st.checkbox("Xác nhận: Xóa danh sách nói chuyện tuần cũ và đưa điểm về 100.")

    if st.button("🔄 BẮT ĐẦU TUẦN MỚI (RESET TOÀN LỚP)", type="primary"):
        if confirm_check:
            with st.spinner("Đang tiến hành đặt lại dữ liệu tuần mới..."):
                df["Điểm thi đua"] = 100
                df["Xếp loại"] = "Tốt"
                df["Lỗi vi phạm"] = "None"
                df.to_csv(DATA_FILE, index=False)
                st.session_state.df = df

                if API_URL and "/exec" in API_URL:
                    ok, msg = reset_new_week_gsheet()
                    if not ok:
                        st.warning(f"Lưu máy tính thành công, chưa đồng bộ Google Sheet: {msg}")
                    else:
                        st.success("🎉 Đã reset thành công sang tuần mới!")
                else:
                    st.success("🎉 Đã reset dữ liệu thành công!")

                time.sleep(1.5)
                st.rerun()
        else:
            st.error("⚠️ Vui lòng tích chọn ô xác nhận ở trên trước khi bấm Reset!")
