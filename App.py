import streamlit as st
import spotipy
# from spotipy.oauth2 import SpotifyOAuth
from spotipy.oauth2 import SpotifyClientCredentials
import pandas as pd
import os
import re

# ==========================================
# 1. 設定（st.secretsから安全に読み込む）
# ==========================================
SPOTIPY_CLIENT_ID = st.secrets["SPOTIPY_CLIENT_ID"]
SPOTIPY_CLIENT_SECRET = st.secrets["SPOTIPY_CLIENT_SECRET"]
SPOTIPY_REDIRECT_URI = st.secrets["SPOTIPY_REDIRECT_URI"]
ADMIN_PASS = st.secrets["ADMIN_PASS"]

PLAYLIST_ID = "4eMAdiJodicdywba8pZ0DU"
CSV_FILE_PATH = "my_anison_data.csv"

# ==========================================
# 2. 関数定義
# ==========================================
@st.cache_data
# def fetch_spotify_playlist():
#     auth_manager = SpotifyOAuth(
#         client_id=SPOTIPY_CLIENT_ID,
#         client_secret=SPOTIPY_CLIENT_SECRET,
#         redirect_uri=SPOTIPY_REDIRECT_URI,
#         scope="playlist-read-private"
#     )
#     sp = spotipy.Spotify(auth_manager=auth_manager)
#     results = sp.playlist_tracks(PLAYLIST_ID)
#     tracks = results["items"]
#     while results["next"]:
#         results = sp.next(results)
#         tracks.extend(results["items"])
    
#     data = []
#     for item in tracks:
#         track_data = item.get("track") or item.get("item")
#         if not track_data or not track_data.get("name"): continue
#         artists = track_data.get("artists", [])
#         data.append({
#             "曲名": track_data["name"],
#             "アーティスト": artists[0]["name"] if artists else "不明"
#         })
#     return pd.DataFrame(data)

def fetch_spotify_playlist():
    # 🌟ログイン画面を出さずに直接サーバー間通信をするモードに変更
    auth_manager = SpotifyClientCredentials(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET
    )
    sp = spotipy.Spotify(auth_manager=auth_manager)
    results = sp.playlist_tracks(PLAYLIST_ID)
    
    # 以下の処理は今までと同じです
    tracks = results["items"]
    while results["next"]:
        results = sp.next(results)
        tracks.extend(results["items"])
    
    data = []
    for item in tracks:
        track_data = item.get("track") or item.get("item")
        if not track_data or not track_data.get("name"): continue
        artists = track_data.get("artists", [])
        data.append({
            "曲名": track_data["name"],
            "アーティスト": artists[0]["name"] if artists else "不明"
        })
    return pd.DataFrame(data)


def get_session_columns(df):
    cols = [c for c in df.columns if "回目" in c]
    return sorted(cols, key=lambda x: int(re.search(r'\d+', x).group()))

# ==========================================
# 3. データの初期化 と サイドバー（認証システム）
# ==========================================
st.set_page_config(layout="wide", page_title="アニソンカラオケ管理")
st.title("🎤 アニソンカラオケ管理アプリ")

# --- 💡 認証システム ---
with st.sidebar:
    st.write("### 🔑 管理者メニュー")
    user_pass = st.text_input("編集用パスワード", type="password")
    
    # パスワードが一致したらTrueになる
    is_admin = (user_pass == ADMIN_PASS)
    
    if is_admin:
        st.success("✅ 管理者モードでログイン中")
        st.write("---")
        if st.button("🔄 Spotifyの最新曲を反映"):
            st.cache_data.clear() 
            latest_df = fetch_spotify_playlist()
            current_df = st.session_state.df
            
            latest_keys = latest_df.set_index(['曲名', 'アーティスト']).index
            current_keys = current_df.set_index(['曲名', 'アーティスト']).index
            
            new_songs = latest_df[~latest_keys.isin(current_keys)]
            added_count = len(new_songs)
            if added_count > 0:
                for col in current_df.columns:
                    if col not in new_songs.columns:
                        new_songs[col] = False if ("回目" in col or col in ["声優", "キャラソン"]) else (0 if col == "歌唱回数" else "")
                current_df = pd.concat([current_df, new_songs], ignore_index=True)
                
            current_keys_updated = current_df.set_index(['曲名', 'アーティスト']).index
            deleted_mask = ~current_keys_updated.isin(latest_keys)
            deleted_count = deleted_mask.sum()
            if deleted_count > 0:
                current_df = current_df[~deleted_mask]
                
            if added_count > 0 or deleted_count > 0:
                st.session_state.df = current_df
                current_df.to_csv(CSV_FILE_PATH, index=False)
                msg = []
                if added_count > 0: msg.append(f"{added_count}件追加")
                if deleted_count > 0: msg.append(f"{deleted_count}件削除")
                st.success(" と ".join(msg) + " しました！")
                st.rerun()
            else:
                st.info("変更はありませんでした。")
    else:
        st.warning("👀 閲覧モード：編集するにはパスワードを入力してください。")

# データ読み込み
if "df" not in st.session_state:
    if os.path.exists(CSV_FILE_PATH):
        df = pd.read_csv(CSV_FILE_PATH)
        new_cols = {"アニメ名": "", "声優": False, "キャラソン": False, "声優・ユニット名": "", "歌唱回数": 0}
        for col, default in new_cols.items():
            if col not in df.columns: df[col] = default
        df["アニメ名"] = df["アニメ名"].fillna("").astype(str)
        df["声優・ユニット名"] = df["声優・ユニット名"].fillna("").astype(str)
        st.session_state.df = df
    else:
        st.info("初回データ構築中...")
        df = fetch_spotify_playlist()
        for col, val in {"アニメ名": "", "声優": False, "キャラソン": False, "声優・ユニット名": "", "1回目": False, "歌唱回数": 0}.items():
            df[col] = val
        st.session_state.df = df
        df.to_csv(CSV_FILE_PATH, index=False)
        st.rerun()

df = st.session_state.df
session_cols = get_session_columns(df)

# ==========================================
# 4. タブ管理
# ==========================================
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎤 歌唱記録", "🏷️ アニメ・属性編集", "📺 アニメ別", "🎙️ 声優・ユニット別", "🔍 検索"])

# --- タブ1: 記録 ---
with tab1:
    top_bar_t1 = st.container()
    search_t1 = st.text_input("🔍 曲名・アーティスト・アニメ名で絞り込む", key="search_t1")
    
    display_sessions = session_cols[-5:]
    display_df = df[["曲名", "アーティスト", "アニメ名", "声優", "キャラソン", "歌唱回数"] + display_sessions]
    
    if search_t1:
        mask = display_df["曲名"].str.contains(search_t1, case=False, na=False) | display_df["アニメ名"].str.contains(search_t1, case=False, na=False) | display_df["アーティスト"].str.contains(search_t1, case=False, na=False)
        display_df = display_df[mask]
        st.info(f"「{search_t1}」で絞り込み中: **{len(display_df)}件** 表示")
    else:
        st.write(f"現在は **{display_sessions[0]} 〜 {display_sessions[-1]}** を表示中")

    # 💡 管理者でなければ、表全体を編集不可(True)にする
    disable_status_t1 = ["曲名", "アーティスト", "アニメ名", "声優", "キャラソン", "歌唱回数"] if is_admin else True

    edited_display_df = st.data_editor(
        display_df,
        disabled=disable_status_t1,
        hide_index=True, use_container_width=True, height=500
    )
    
    with top_bar_t1:
        c1, c_empty, c2 = st.columns([3, 5, 3])
        if is_admin: # 管理者のみボタン表示
            if c1.button("➕ 新しい回を追加"):
                df[f"{len(session_cols)+1}回目"] = False
                st.session_state.df = df
                st.rerun()
            if c2.button("💾 記録を保存", key="save_t1", type="primary", use_container_width=True):
                for col in display_sessions:
                    df.loc[edited_display_df.index, col] = edited_display_df[col]
                df["歌唱回数"] = df[session_cols].sum(axis=1)
                st.session_state.df = df
                df.to_csv(CSV_FILE_PATH, index=False)
                st.success("保存完了！")
                st.rerun()

# --- タブ2: アニメ・属性編集 ---
with tab2:
    top_bar_t2 = st.container()
    existing_animes = df[df["アニメ名"].notna() & (df["アニメ名"] != "")]["アニメ名"].unique().tolist()
    if existing_animes:
        with st.expander("📝 登録済みのアニメ名一覧"):
            st.write(", ".join(sorted(existing_animes)))

    disable_status_t2 = ["曲名", "アーティスト"] if is_admin else True

    edit_attr_df = st.data_editor(
        df[["曲名", "アーティスト", "アニメ名", "声優", "キャラソン"]],
        column_config={
            "アニメ名": st.column_config.TextColumn("アニメ名"),
            "声優": st.column_config.CheckboxColumn("声優"),
            "キャラソン": st.column_config.CheckboxColumn("キャラソン")
        },
        disabled=disable_status_t2,
        hide_index=True, use_container_width=True, height=500
    )
    
    with top_bar_t2:
        c1, c2 = st.columns([7, 3])
        c1.write("曲ごとの欄に直接アニメ名を入力してください。")
        if is_admin:
            if c2.button("💾 属性を保存", key="save_t2", type="primary", use_container_width=True):
                df["アニメ名"] = edit_attr_df["アニメ名"]
                df["声優"] = edit_attr_df["声優"]
                df["キャラソン"] = edit_attr_df["キャラソン"]
                st.session_state.df = df
                df.to_csv(CSV_FILE_PATH, index=False)
                st.success("保存完了！")
                st.rerun()

# --- タブ3: アニメ別 ---
with tab3:
    anime_list = df[df["アニメ名"].notna() & (df["アニメ名"] != "")]["アニメ名"].unique()
    for anime in sorted(anime_list):
        sub = df[df["アニメ名"] == anime]
        with st.expander(f"📺 {anime} ({len(sub)}曲)"):
            st.dataframe(sub[["曲名", "アーティスト", "歌唱回数", "声優・ユニット名"]], hide_index=True, use_container_width=True)

# --- タブ4: 声優・ユニット別 ---
with tab4:
    cv_songs_df = df[df["声優"] == True]
    if cv_songs_df.empty:
        st.warning("「🏷️ アニメ・属性編集」タブで「声優」にチェックを入れてください。")
    else:
        top_bar_t4 = st.container()
        disable_status_t4 = ["曲名", "アーティスト", "アニメ名"] if is_admin else True
        
        edit_cv_df = st.data_editor(
            cv_songs_df[["曲名", "アーティスト", "アニメ名", "声優・ユニット名"]],
            column_config={"声優・ユニット名": st.column_config.TextColumn("声優・ユニット名")},
            disabled=disable_status_t4,
            hide_index=True, use_container_width=True, key="cv_editor"
        )
        with top_bar_t4:
            c1, c2 = st.columns([7, 3])
            c1.write("声優名やユニット名を直接入力してください。")
            if is_admin:
                if c2.button("💾 声優情報を保存", key="save_t4", type="primary", use_container_width=True):
                    df.loc[df["声優"] == True, "声優・ユニット名"] = edit_cv_df["声優・ユニット名"].values
                    st.session_state.df = df
                    df.to_csv(CSV_FILE_PATH, index=False)
                    st.success("保存完了！")
                    st.rerun()
        
        cv_list = df[df["声優・ユニット名"].notna() & (df["声優・ユニット名"] != "")]["声優・ユニット名"].unique()
        for cv in sorted(cv_list):
            sub_cv = df[df["声優・ユニット名"] == cv]
            with st.expander(f"🎙️ {cv} ({len(sub_cv)}曲)"):
                st.dataframe(sub_cv[["曲名", "アーティスト", "アニメ名", "歌唱回数"]], hide_index=True, use_container_width=True)

# --- タブ5: 検索 ---
with tab5:
    q = st.text_input("検索ワード（曲名・アニメ名・アーティスト）")
    if q:
        mask = df["曲名"].str.contains(q, case=False, na=False) | df["アニメ名"].str.contains(q, case=False, na=False) | df["アーティスト"].str.contains(q, case=False, na=False)
        res = df[mask]
        st.success(f"{len(res)}件ヒット！")
        st.dataframe(res[["曲名", "アーティスト", "アニメ名", "声優・ユニット名", "歌唱回数"]], hide_index=True, use_container_width=True)