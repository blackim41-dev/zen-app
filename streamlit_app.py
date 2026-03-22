import streamlit as st
st.set_page_config(page_title="顧客・来店管理", layout="wide")

st.markdown("""
<style>

/* 高さ */
div[data-baseweb="select"] > div {
    height: 90px !important;
    min-height: 90px !important;
    align-items: flex-start !important;
    padding-top: 8px !important;
}

/* ★選択済み表示部分を強制折り返し */
div[data-baseweb="select"] div {
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: unset !important;
    word-break: break-word !important;
}

/* ★ドロップダウンの中も折り返し */
ul[role="listbox"] li {
    white-space: normal !important;
    word-break: break-word !important;
}

</style>
""", unsafe_allow_html=True)

import requests
from datetime import date, datetime
import pandas as pd

session = requests.Session()

GAS_BASE_URL = "https://script.google.com/macros/s/AKfycbxo0O6i7nw7-pRb9XbwIbESwwgVyugybuqGwKWGibzqSQHctS0eRpjGw5DjVZdoyTfZqw/exec"
# 自ファイル
# GAS_BASE_URL = "https://script.google.com/macros/s/AKfycbxBxpHRVXoWCru_0jL7lZc0U5vA_FXaOBRaoCgEVBEZGZ-0MpUAYUKjNuqAxetIyBMgYQ/exec"

GAS_POST_URL = GAS_BASE_URL

@st.cache_data(ttl=60)
def load_customer():
    CUSTOMER_COLUMNS = ["氏名","ふりがな","ニックネーム","会社名","電話番号","住所",
                        "生年月日","初回来店日","顧客_ID","削除"]

    url = f"{GAS_BASE_URL}?action=get_customer"
    res = session.get(url, timeout=30)
    res.raise_for_status()

    data = res.json()
    df = pd.DataFrame(data)

    if df.empty:
        df = pd.DataFrame(columns=CUSTOMER_COLUMNS)

    if "削除" not in df.columns:
        df["削除"] = ""

    df["削除"] = df["削除"].apply(lambda x: "1" if str(x).strip() == "1" else "0")

    return df

@st.cache_data(ttl=60)
def load_visit():
    VISIT_COLUMNS = ["来店日","曜日","同伴_氏名","担当_氏名",
                    "延長回数","キープ銘柄","プレゼント_受","プレゼント_渡",
                    "メモ_来店","来店履歴_ID","顧客_ID","削除"]

    url = f"{GAS_BASE_URL}?action=get_visit"
    res = session.get(url, timeout=30)
    res.raise_for_status()

    data = res.json()
    df = pd.DataFrame(data)

    if df.empty:
        df = pd.DataFrame(columns=VISIT_COLUMNS)

    if "削除" not in df.columns:
        df["削除"] = ""

    df["削除"] = df["削除"].apply(lambda x: "1" if str(x).strip() == "1" else "0")

    return df

# =====================
# DataFrame を読み込む
# =====================
customer_df = load_customer()
visit_df = load_visit()

# ★ 日付列だけ明示的に None に統一
customer_df["初回来店日"].fillna("", inplace=True)
if not visit_df.empty:
    visit_df["来店日"].fillna("", inplace=True)

# --- customer ---
text_cols = customer_df.columns.difference(["生年月日", "初回来店日"])
customer_df[text_cols] = customer_df[text_cols].fillna("")

# --- visit ---
text_cols_visit = visit_df.columns.difference(["来店日"])
visit_df[text_cols_visit] = visit_df[text_cols_visit].fillna("")

# 通常画面用
active_customer_df = customer_df[customer_df["削除"] != "1"]
active_visit_df = visit_df[visit_df["削除"] != "1"]

# 削除一覧用
deleted_customer_df = customer_df[customer_df["削除"] == "1"]
deleted_visit_df = visit_df[visit_df["削除"] == "1"]

# =====================
# ユーティリティ
# =====================
def next_id(df, col, prefix):
    if df.empty:
        return f"{prefix}00001"
    nums = df[col].astype(str).str.replace(prefix, "", regex=False)
    nums = nums[nums.str.isnumeric()].astype(int)
    return f"{prefix}{nums.max()+1:05d}"

def safe_date(v):
    """
    st.date_input に渡す専用
    → 必ず datetime.date を返す
    """
    if v is None:
        return date.today()

    if isinstance(v, date):
        return v

    if isinstance(v, datetime):
        return v.date()

    if isinstance(v, str) and v.strip() != "":
        try:
            return datetime.strptime(v[:10], "%Y-%m-%d").date()
        except:
            return date.today()
    return date.today()

def safe_bool(v):
    return str(v).lower() in ("true", "1", "yes")

def safe_int(v, default=0):
    try:
        if v == "" or v is None or pd.isna(v):
            return default
        return int(v)
    except:
        return default

def get_weekday(d):
    jp = ["月", "火", "水", "木", "金", "土", "日"]
    return jp[d.weekday()]

def date_to_str(d):
    if isinstance(d, date):
        return d.strftime("%Y-%m-%d")
    return ""

# =====================
# session_state 定義
# =====================
CUSTOMER_STATE_MAP = {
    "input_name": ("氏名", ""),
    "input_kana": ("ふりがな", ""),
    "input_nick": ("ニックネーム", ""),
    "input_job": ("会社名", ""),
    "input_tel": ("電話番号", ""),
    "input_addr": ("住所", ""),
    "input_birth": ("生年月日",date(2000,1,1)),
    "input_first_visit": ("初回来店日", date.today()),
}

VISIT_STATE_MAP = {
    "input_visit_date": ("来店日", date.today()),
    "input_wday": ("曜日", ""),    
    "input_accompany": ("同伴_氏名", ""),
    "input_staff": ("担当_氏名", ""),
    "input_ext": ("延長回数", 0),
    "input_keep": ("キープ銘柄", ""),
    "input_preget": ("プレゼント_受", ""),
    "input_pre": ("プレゼント_渡", ""),
    "input_memo_vis": ("メモ_来店", ""),
}

def init_state_from_row(state_map, row):
    """
    row（dict）から session_state を一括初期化
    すでに存在するキーは触らない
    """
    for key, (col, default) in state_map.items():
            val = row.get(col, default)

            # 日付だけ特別扱い
            if isinstance(default, date):
                val = safe_date(val)

            st.session_state[key] = val

# =====================
# サイドバー
# =====================
menu = st.sidebar.radio("メニュー",["顧客情報入力","来店情報入力","顧客別来店履歴","日付別来店一覧","削除データ一覧"])

# ★ メニュー切替を検知して初期化
if "prev_menu" not in st.session_state:
    st.session_state.prev_menu = menu

# メニュー切替検知
menu_changed = st.session_state.prev_menu != menu

if menu_changed:
    # 状態リセット
    st.session_state.pop("loaded_customer_id", None)
    st.session_state.pop("selected_visit_id", None)
    st.session_state.pop("search_customer_name", None)
    st.session_state.pop("search_visit_name", None)
    st.session_state.customer_mode_radio = "新規顧客入力"

    # ★ 最後に prev_menu 更新
    st.session_state.prev_menu = menu

# =====================
# 顧客情報入力
# =====================
if menu == "顧客情報入力":

    if "customer_mode_radio" not in st.session_state:
        st.session_state.customer_mode_radio = "新規顧客入力"

    # --- 顧客区分（radioは1回だけ！） ---
    customer_mode = st.radio(
        "顧客区分",
        ["新規顧客入力","既存顧客編集"],
        index=0,
        key="customer_mode_radio"
    )

    # 顧客モード変更時はメッセージ消す
    if st.session_state.get("last_customer_mode") != customer_mode:
        st.session_state.pop("flash_message", None)
    st.session_state.last_customer_mode = customer_mode

    cid = st.session_state.get("current_customer_id", "")

    # --- 削除状態チェック ---
    is_deleted = False
    if customer_mode == "既存顧客編集" and cid:
        target = customer_df[customer_df["顧客_ID"] == cid]
        if not target.empty:
            customer_record = target.iloc[0]
            is_deleted = str(customer_record.get("削除", "0")) == "1"

    # --- タイトル ---
    if is_deleted:
        st.markdown(
            '## 顧客情報入力 <span style="color:red;">⚠削除済</span>',
            unsafe_allow_html=True
        )
    else:
        st.header("顧客情報入力")

    prev = st.session_state.get("prev_customer_mode")

    if prev != customer_mode:
        if customer_mode == "新規顧客入力":
            for key in CUSTOMER_STATE_MAP:
                st.session_state.pop(key, None)

    st.session_state.prev_customer_mode = customer_mode

    if customer_mode == "既存顧客編集" and customer_df.empty:
        st.info("先に新規顧客を登録してください")
        st.stop()

    row = {}

    if customer_mode == "既存顧客編集" and not customer_df.empty:
        search_name = st.text_area("≪ 顧客検索 ≫　氏名・ふりがな・ニックネーム検索（部分一致：空白を挟んで入力で複数検索可）", "")
        search_col = customer_df["氏名"].fillna("") + customer_df["ふりがな"].fillna("")+ customer_df["ニックネーム"].fillna("")

        if search_name:
            import re
            search_words = re.split(r"\s+", search_name.strip())
            mask = pd.Series(False, index=customer_df.index)
            for w in search_words:
                if w:
                    mask |= search_col.str.contains(w, case=False, na=False)
            filtered_df = customer_df[mask]
        else:
            filtered_df = customer_df

        name_labels = ["（未選択）"]
        name_map = {}

        for _, r in filtered_df.sort_values("ふりがな").iterrows():
            label = f'{r["氏名"]}：{r["ふりがな"]}（{r["ニックネーム"]}）'
            name_labels.append(label)
            name_map[label] = r["顧客_ID"]

        selected_label = st.selectbox("≪ 顧客選択 ≫",     
            name_labels,key="customer_name_big_select_customer")

        if selected_label != "（未選択）":
            cid = name_map[selected_label]
            row = customer_df[customer_df["顧客_ID"] == cid].iloc[0].to_dict()

            cid = row["顧客_ID"]
            st.session_state.current_customer_id = cid     

    # ★ 顧客切替フラグ
    if (cid and st.session_state.get("loaded_customer_id") != cid
            and customer_mode == "既存顧客編集"):
        st.session_state.loaded_customer_id = cid

        # ---- 顧客情報を一括セット ----
        st.session_state.update({
            "input_name": row.get("氏名", ""),
            "input_kana": row.get("ふりがな", ""),
            "input_nick": row.get("ニックネーム", ""),
            "input_job": row.get("会社名", ""),
            "input_tel": row.get("電話番号", ""),
            "input_addr": row.get("住所", ""),    
            "input_birth": safe_date(row.get("生年月日")),
            "input_first_visit": safe_date(row.get("初回来店日")),
        })

        st.session_state.customer_loaded = True

        if st.session_state.get("customer_loaded"):
            del st.session_state["customer_loaded"]
            st.rerun()

        # ★ 顧客IDは session_state から取得
        cid = st.session_state.get("current_customer_id", "")

    # =====================
    # 顧客情報（事前定義）
    # =====================
    if customer_mode == "新規顧客入力":
        init_key = "customer_initialized"

        if st.session_state.get(init_key) != True:
            for key in CUSTOMER_STATE_MAP:
                st.session_state.pop(key, None)

            init_state_from_row(CUSTOMER_STATE_MAP, {})
            st.session_state[init_key] = True

        cid = next_id(customer_df, "顧客_ID", "C")
        st.session_state.current_customer_id = cid        
        is_deleted = False

    else:
        # 既存顧客に切り替わったら初期化フラグ解除
        st.session_state.pop("customer_initialized", None)

        # ★ 必ず session_state から
        cid = st.session_state.get("current_customer_id")

        if not cid:
            st.error("編集する顧客が特定できません")
            st.stop()

        target = customer_df.query("顧客_ID == @cid")

        if target.empty:
            st.warning("顧客を選択してください")
            st.stop()

        customer_record = target.iloc[0]
        is_deleted = str(customer_record.get("削除", "0")) == "1"

    col1, col2 = st.columns(2)

    with col1:
        name = st.text_area("氏名", key="input_name",height=60, disabled=is_deleted)
        kana = st.text_area("ふりがな", key="input_kana",height=60, disabled=is_deleted)        
        nick = st.text_area("ニックネーム", key="input_nick",height=60, disabled=is_deleted)
        job = st.text_area("会社名", key="input_job",height=60, disabled=is_deleted)


    with col2:
        tel = st.text_area("電話番号", key="input_tel",height=60, disabled=is_deleted)
        addr = st.text_area("住所", key="input_addr",height=60, disabled=is_deleted)
        birth = st.date_input("生年月日",min_value=date(1900, 1, 1),max_value=date.today(),
                                key="input_birth",disabled=is_deleted)
        first = st.date_input("初回来店日",min_value=date(2000, 1, 1),max_value=date.today(),
                                key="input_first_visit", disabled=is_deleted)

    # ==================
    # ボタン_顧客情報
    # ==================
    save_customer = st.button("顧客情報_保存", disabled=is_deleted)
    if customer_mode == "新規顧客入力":
        delete_btn = st.button("顧客情報_削除", disabled=not is_deleted)
    else:
        delete_btn = st.button("顧客情報_削除", disabled=is_deleted)

    restore_btn = st.button("顧客情報_復元", disabled=not is_deleted)

    # 保存メッセージ表示設定
    if "flash_message" in st.session_state:
        st.success(st.session_state.flash_message)

    if delete_btn and not is_deleted:
        payload = {
            "mode": "customer_delete",
            "顧客_ID": cid,
            "削除": "1"
        }
        r = session.post(GAS_POST_URL, json=payload, timeout=30)
        if r.status_code != 200:
            st.error("保存エラー")
            st.write(r.text)
            st.stop()

        load_customer.clear()
        st.session_state.flash_message = "削除しました ✅"  
        st.rerun()

    if restore_btn and is_deleted:
        payload = {
            "mode": "customer_restore",
            "顧客_ID": cid,
            "削除": "0"
        }
        r = session.post(GAS_POST_URL, json=payload, timeout=30)
        if r.status_code != 200:
            st.error("保存エラー")
            st.write(r.text)
            st.stop()

        load_customer.clear()
        st.session_state.flash_message = "復元しました ✅"    
        st.rerun()
      
    # =====================
    # 顧客情報の保存
    # =====================
    if save_customer:
        cid = st.session_state.get("current_customer_id")

        if not cid:
            st.error("顧客IDが取得できません")
            st.stop()

        payload = {
            "mode": "customer_only",

            "氏名": name,
            "ふりがな": kana,            
            "ニックネーム": nick,
            "会社名": job,
            "電話番号": tel,
            "住所": addr,
            "生年月日": date_to_str(birth),
            "初回来店日": date_to_str(first),

            "顧客_ID": cid,
            "削除": "0"
        }

        with st.spinner("保存中です…"):
            r = session.post(GAS_POST_URL, json=payload, timeout=30)
            if r.status_code != 200:
                st.error("保存エラー")
                st.write(r.text)
                st.stop()

        # ★ ここで必ずキャッシュ破棄＋再読込
        load_customer.clear()        
        st.session_state.loaded_customer_id = cid
        st.session_state.flash_message = "保存しました ✅"
        st.rerun()

# =====================
# 来店情報入力
# =====================
elif menu == "来店情報入力":
    is_deleted = False
    st.header("来店情報入力")

    # --- フラッシュメッセージ 初期化 ---
    if "flash_message" in st.session_state:
        st.session_state.flash_message = None
        
    # --- visit_mode 初期化 ---
    if "visit_mode" not in st.session_state:
        st.session_state.visit_mode = "新規来店入力"

    # 保存後は編集状態を維持
    if st.session_state.get("return_to_edit"):
        st.session_state.visit_mode = "既存来店履歴編集"
        del st.session_state.return_to_edit

    # --- radio（1回だけ） ---
    visit_mode = st.radio(
        "来店入力モード",
        ["新規来店入力", "既存来店履歴編集"],
        key="visit_mode"
    )

    # 初回用
    if "last_visit_mode" not in st.session_state:
        st.session_state.last_visit_mode = visit_mode

    # モード変更検知
    if st.session_state.last_visit_mode != visit_mode:
        st.session_state.pop("flash_message", None)
        st.session_state.last_visit_mode = visit_mode

    # ★ 顧客IDは必ず session_state から取得（未選択時は ""）
    cid = st.session_state.get("current_customer_id", "")    
    
    search_name = st.text_area("≪ 顧客検索 ≫　氏名・ニックネーム検索（部分一致：空白を挟んで入力で複数検索可）", "")
    search_col = active_customer_df["氏名"].fillna("") + active_customer_df["ふりがな"].fillna("")+ active_customer_df["ニックネーム"].fillna("")

    if search_name:
        import re
        search_words = re.split(r"\s+", search_name.strip())
        mask = pd.Series(False, index=active_customer_df.index)
        for w in search_words:
            if w:
                mask |= search_col.str.contains(w, case=False, na=False)
        filtered_df = active_customer_df[mask]
    else:
        filtered_df = active_customer_df

    name_labels = ["（未選択）"]
    name_map = {}

    sorted_df = filtered_df.sort_values("ふりがな")
    labels = sorted_df["氏名"] + "：" + sorted_df["ふりがな"] + "（" + sorted_df["ニックネーム"] + "）"
    name_labels = ["（未選択）"] + labels.tolist()
    name_map = dict(zip(labels, sorted_df["顧客_ID"]))

    selected_label = st.selectbox("≪ 顧客選択 ≫",
        name_labels, key="customer_name_big_select_visit")

    if selected_label != "（未選択）":
        cid = name_map[selected_label]
        row = customer_df[customer_df["顧客_ID"] == cid].iloc[0].to_dict()
        st.session_state.current_customer_id = cid

        cid = row["顧客_ID"]
        st.session_state.current_customer_id = cid     

    # =====================
    # 来店情報（事前定義）
    # =====================  
    vid = st.session_state.get("current_visit_id", "")

    if visit_mode == "既存来店履歴編集":

        if not cid:
            st.info("先に顧客を選択してください")
            st.stop()

        target_visits = visit_df[visit_df["顧客_ID"] == cid].copy()

        visit_record = visit_df[visit_df["来店履歴_ID"] == st.session_state.get("selected_visit_id")]

        if not visit_record.empty:
            visit_record = visit_record.iloc[0]
            is_deleted = str(visit_record.get("削除", "0")) == "1"
        else:
            is_deleted = False

        if target_visits.empty:
            st.info("編集できる来店履歴がありません")
        else:
            # --- 日付を datetime に変換 ---
            target_visits["来店日_dt"] = pd.to_datetime(target_visits["来店日"], errors="coerce")

            # --- 新しい順に並べる ---
            target_visits = target_visits.sort_values("来店日_dt", ascending=False)

            # --- 表示ラベル作成 ---
            dates = target_visits["来店日_dt"].dt.date.astype(str)
            ids = target_visits["来店履歴_ID"]
            labels = dates + "（" + target_visits["来店日_dt"].apply(get_weekday) + "）" + ids
            deleted_mask = target_visits["削除"].astype(str) == "1"
            labels = labels.where(~deleted_mask, labels + "【削除済】")
            visit_labels = labels

            visit_map = dict(zip(visit_labels, target_visits["来店履歴_ID"]))

            selected_label = st.selectbox("編集する来店履歴を選択",
                ["（未選択）"] + visit_labels.tolist(),key="visit_edit_select"
            )

            if selected_label == "（未選択）":
                st.session_state.selected_visit_id = None
            else:
                vid = visit_map[selected_label]
                st.session_state.selected_visit_id = vid

                visit_row = target_visits[
                    target_visits["来店履歴_ID"] == vid
                ].iloc[0].to_dict()

                # --- 削除判定（最終版）---
                is_deleted = False

                if visit_mode == "既存来店履歴編集":
                    vid = st.session_state.get("selected_visit_id")

                    if vid:
                        target = visit_df[visit_df["来店履歴_ID"] == vid]
                        if not target.empty:
                            is_deleted = str(target.iloc[0].get("削除", "0")) == "1"

                if is_deleted:
                    st.markdown(
                        '## <span style="color:red;">⚠削除済</span>',
                        unsafe_allow_html=True
                    )

                # ★ 違う来店IDを選んだ時だけ初期化
                if st.session_state.get("loaded_visit_id") != vid:

                    for key, (col, default) in VISIT_STATE_MAP.items():
                        val = visit_row.get(col, default)

                        # 日付はdate型に変更
                        if isinstance(default, date):
                            val = safe_date(val)
                        # フォームのkeyと一致させる
                        st.session_state[key] = val

                    st.session_state.loaded_visit_id = vid

                is_deleted = str(visit_row.get("削除", "0")) == "1"

    # --- 新規来店入力 初期化 ---
    init_key = f"visit_initialized_for_{cid}"

    editing = visit_mode == "既存来店履歴編集" and st.session_state.get("selected_visit_id")

    if visit_mode == "新規来店入力":
        st.session_state.pop("selected_visit_id", None)

        if st.session_state.get(init_key) != True:
            for key in VISIT_STATE_MAP:
                st.session_state.pop(key, None)

            init_state_from_row(VISIT_STATE_MAP, {})
            st.session_state[init_key] = True
    else:
        st.session_state.pop(init_key, None)
      
    col1, col2 = st.columns(2)

    with col1:
        visit_date = st.date_input("来店日", key="input_visit_date", disabled=is_deleted)
        accompany = st.text_area("同伴_氏名", key="input_accompany",height=60, disabled=is_deleted)
        staff = st.text_area("担当_氏名", key="input_staff",height=60, disabled=is_deleted)
        ext = st.number_input("延長回数", min_value=0, max_value=10, key="input_ext", disabled=is_deleted)

    with col2:
        keep = st.text_area("キープ銘柄", key="input_keep",height=60, disabled=is_deleted)
        preget = st.text_area("プレゼント_受", key="input_preget",height=60, disabled=is_deleted)
        pre = st.text_area("プレゼント_渡", key="input_pre",height=60, disabled=is_deleted)
        memovis = st.text_area("メモ_来店", key="input_memo_vis",height=60, disabled=is_deleted) 

    # ボタン_来店情報
    save_visit = st.button("来店情報_保存", disabled= is_deleted)
    if visit_mode == "新規来店入力":
        delete_btn = st.button("来店情報_削除", disabled=not is_deleted)
    else:
        delete_btn = st.button("来店情報_削除", disabled= is_deleted)
    restore_btn = st.button("来店情報_復元", disabled=not is_deleted)

    # 保存メッセージ表示
    if st.session_state.get("flash_message"):
        st.success(st.session_state.flash_message)

    if visit_mode == "既存来店履歴編集" and vid:
        if delete_btn:
            vid = st.session_state.get("selected_visit_id")

            if not vid:
                st.error("来店履歴が選択されていません")
                st.stop()

            payload = {
                "mode": "visit_delete",
                "来店履歴_ID": vid
            }

            r = session.post(GAS_POST_URL, json=payload, timeout=30)
            if r.status_code != 200:
                st.error("保存エラー")
                st.write(r.text)
                st.stop()

            load_visit.clear()
            st.session_state.flash_message = "削除しました ✅"
            st.rerun()

    if restore_btn and is_deleted:
        payload = {
            "mode": "visit_restore",
            "来店履歴_ID": vid,
        }
        r = session.post(GAS_POST_URL, json=payload, timeout=30)
        if r.status_code != 200:
            st.error("保存エラー")
            st.write(r.text)
            st.stop()

        load_visit.clear()
        st.session_state.flash_message = "復元しました ✅"  
        st.rerun()
            
    def date_to_str(d):
        if isinstance(d, date):
            return d.strftime("%Y-%m-%d")
        return ""
    
    # =====================
    # 来店情報の保存
    # =====================
    if save_visit and not st.session_state.get("saving_visit", False):
        st.session_state.saving_visit = True
        cid = st.session_state.get("current_customer_id")

        if not cid:
            st.error("顧客が選択されていません")
            st.stop()

        if visit_mode == "新規来店入力":
            vid = next_id(visit_df, "来店履歴_ID", "V")
        else:
            vid = st.session_state.get("selected_visit_id")
            if not vid:
                st.error("編集する来店履歴が特定できません")
                st.stop()

        payload = {
            "mode": "visit_only",

            "来店日": visit_date.strftime("%Y-%m-%d"),
            "曜日": get_weekday(visit_date),
            "同伴_氏名": accompany,
            "担当_氏名": staff,
            "延長回数": ext,
            "キープ銘柄": keep,
            "プレゼント_受": preget,
            "プレゼント_渡": pre,
            "メモ_来店": memovis,

            "来店履歴_ID": vid,
            "顧客_ID": cid,
            "削除": "0"
        }
    
        with st.spinner("保存中です…"):
            r = session.post(GAS_POST_URL, json=payload, timeout=30)

            if r.status_code != 200:
                st.error("保存エラーが発生しました")
                st.write(r.text)
                st.stop()

        # 来店保存後
        st.session_state.saving_visit = False
        load_visit.clear()

        st.session_state.selected_visit_id = vid

        if visit_mode == "新規来店入力":
            st.session_state.flash_message = "保存しました ✅"     
        else:
            st.session_state.flash_message = "更新しました ✅"     
            st.session_state.saving_visit = False

        st.rerun()

# ==========================
# 顧客別来店履歴（氏名で選択）
# ==========================
elif menu == "顧客別来店履歴":
    st.header("顧客別来店履歴")

    # ① 検索ボックス（常に定義するのが重要）
    search_name = st.text_area("≪ 顧客検索 ≫　氏名・ふりがな・ニックネーム検索（部分一致：空白を挟んで入力で複数検索可）",key="search_customer_name")
    search_col = active_customer_df["氏名"].fillna("") + active_customer_df["ふりがな"].fillna("")+ active_customer_df["ニックネーム"].fillna("")

    # ② 検索結果で顧客を絞り込む
    if search_name:
        import re
        search_words = re.split(r"\s+", search_name.strip())
        mask = pd.Series(False, index=active_customer_df.index)
        for w in search_words:
            if w:
                mask |= search_col.str.contains(w, case=False, na=False)
        filtered_df = active_customer_df[mask]
    else:
        filtered_df = active_customer_df

    # ③ selectbox（必ず表示・未選択あり）
    # 来店回数を集計
    visit_count = active_visit_df.groupby("顧客_ID").size().to_dict()

    # 表示ラベル作成
    name_labels = ["（未選択）"]
    name_map = {}

    # 五十音順で並べる
    filtered_df = filtered_df.sort_values("ふりがな", ascending=True)

    for _, row in filtered_df.iterrows():
        cid = row["顧客_ID"]
        name = row["氏名"]
        kana = row["ふりがな"]        
        nick = row["ニックネーム"]
        count = visit_count.get(cid, 0)

        label = f"{name}：{kana}（{nick}）（{count}回）"
        name_labels.append(label)
        name_map[label] = cid

    selected_label = st.selectbox("≪ 顧客選択 ≫", name_labels,
        key="customer_name_big_select_history")

    if not selected_label:
        st.info("顧客を選択してください")
    else:
        if selected_label == "（未選択）":
            st.info("顧客を選択してください")
            st.stop()

        cid = name_map[selected_label]

        target = active_visit_df[
            active_visit_df["顧客_ID"] == cid
        ].copy()

        if target.empty:
            st.warning("来店履歴がありません")
            st.stop()

        # 日付を datetime に
        target["来店日"] = pd.to_datetime(target["来店日"], errors="coerce")

        # 古い順で番号
        target = target.sort_values("来店日", ascending=True)
        target["No"] = range(1, len(target) + 1)

        # 表示は新しい順
        target = target.sort_values(["来店日", "No"], ascending=[False, False])

        # 時刻を消す
        target["来店日"] = target["来店日"].dt.date

        # 不要列削除
        target = target.drop(columns=["顧客_ID", "来店履歴_ID", "削除"], errors="ignore")

        # No を左に
        cols = ["No"] + [c for c in target.columns if c != "No"]
        target = target[cols]

        st.dataframe(target, hide_index=True)

# =====================
# 日付別来店一覧
# =====================
elif menu == "日付別来店一覧":
    st.header("日付別来店一覧")

    # ★① データ準備
    df = active_visit_df.copy()
    df["来店日"] = pd.to_datetime(df["来店日"]).dt.date

    # ★② 来店日一覧（存在する日付のみ）
    date_list = sorted(df["来店日"].dropna().unique(), reverse=True)

    if not date_list:
        st.warning("来店データがありません")
        st.stop()

    # ★③ 表示用ラベル
    date_count = df.groupby("来店日").size().to_dict()
    date_labels = ["（日付を選択）"] + [f"{d}({get_weekday(pd.to_datetime(d))})（{date_count[d]}件）"for d in date_list]

    # ★④ selectbox
    selected_label = st.selectbox("≪ 来店日選択 ≫",date_labels,index=0,key="visit_date_select")

    if selected_label == "（日付を選択）":
        st.info("来店日を選択してください")
        st.stop()

    # ★⑤ 表示ラベル → 実日付
    selected_date = date_list[date_labels.index(selected_label) - 1]

    # ★⑥ 来店一覧抽出
    target = df[df["来店日"] == selected_date].copy()

    target["来店日"] = pd.to_datetime(target["来店日"])

    # 顧客ID → 氏名・ふりがな・ニックネームに変換
    target = target.merge(customer_df[["顧客_ID", "氏名","ふりがな","ニックネーム"]], on="顧客_ID", how="left")

    # ★ふりがな昇順で並べる
    target = target.sort_values("ふりがな", ascending=True)

    # ★その順でNoを振る
    target["No"] = range(1, len(target) + 1)

    # 来店日・曜日・顧客ID・来店履歴ID・削除は消す
    target = target.drop(columns=["来店日", "曜日","顧客_ID", "来店履歴_ID","削除"], errors="ignore")

    # ★No → 氏名 → その他の順に並び替え
    cols = ["No", "氏名","ふりがな","ニックネーム"] + [c for c in target.columns if c not in ["No", "氏名","ふりがな","ニックネーム"]]
    target = target[cols]

    # 表示は新しい順
    target = target.sort_values(["No"], ascending=[False])
    
    st.dataframe(target, hide_index=True)

# =====================
# 削除データ一覧
# =====================
elif menu == "削除データ一覧":
    st.header("削除データ一覧")

    # 日付だけ表示に変換
    date_cols = ["生年月日", "初回来店日", "来店日"]

    for col in date_cols:
        if col in deleted_customer_df.columns:
            deleted_customer_df[col] = pd.to_datetime(
                deleted_customer_df[col], errors="coerce"
            ).dt.date

        if col in deleted_visit_df.columns:
            deleted_visit_df[col] = pd.to_datetime(
                deleted_visit_df[col], errors="coerce"
            ).dt.date

    # ==================
    # 表示用
    # ==================
    # 顧客情報-------
    view_customer = deleted_customer_df.drop(
        columns=["顧客_ID", "削除"],
        errors="ignore"
    )

    # 来店履歴情報-------
    # 顧客名を結合
    deleted_visit_df = deleted_visit_df.merge(
        customer_df[["顧客_ID", "氏名", "ふりがな","ニックネーム"]],
        on="顧客_ID",
        how="left"
    )
    view_visit = deleted_visit_df.drop(
        columns=["顧客_ID", "来店履歴_ID", "削除"],
        errors="ignore"
    )

    # 並び替え
    cols = ["氏名", "ふりがな","ニックネーム"] + [c for c in view_visit.columns if c not in ["氏名","ふりがな","ニックネーム"]]

    view_visit = view_visit[cols]

    st.subheader("顧客")
    st.dataframe(view_customer, hide_index=True)
    st.subheader("来店履歴")
    st.dataframe(view_visit, hide_index=True)