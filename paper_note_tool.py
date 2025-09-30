# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from datetime import datetime
import json
import uuid
import io
import hashlib
import re
from collections import Counter
import math
import time  # <-- for 1s pause before rerun

# -----------------------
# Page
# -----------------------
st.set_page_config(page_title="Paper Note Tool", layout="wide")
st.title("📚 Paper Note Tool")
st.markdown(
    "This tool **automatically saves** to **Excel / CSV / JSON** after add/edit/delete/import. "
)

# -----------------------
# Paths & constants
# -----------------------
DATA_DIR = "paper_notes_data"
os.makedirs(DATA_DIR, exist_ok=True)
CSV_PATH = os.path.join(DATA_DIR, "papers.csv")
JSON_PATH = os.path.join(DATA_DIR, "papers.json")
XLSX_PATH = os.path.join(DATA_DIR, "papers.xlsx")

REQUIRED_COLUMNS = [
    "id", "saved_at", "title", "authors", "year", "journal",
    "population", "main_variables", "measures", "takeaway",
    "tags", "doi_or_url", "notes"
]

CARD_BG_FALLBACKS = ["#f9f9f9", "#e0f7fa", "#fff3e0", "#f3e5f5", "#e8f5e9"]
TAG_COLOR_PALETTE = [
    "#E3F2FD", "#FFF3E0", "#F3E5F5", "#E8F5E9", "#FCE4EC",
    "#E0F2F1", "#FFF8E1", "#EDE7F6", "#F1F8E9", "#ECEFF1"
]
TAG_BORDER_PALETTE = [
    "#90CAF9", "#FFB74D", "#BA68C8", "#81C784", "#F06292",
    "#4DB6AC", "#FFD54F", "#9575CD", "#AED581", "#90A4AE"
]

# -----------------------
# Utils
# -----------------------
def hard_rerun():
    """Force a rerun, with a query param fallback."""
    try:
        st.rerun()
    except Exception:
        st.query_params.update({"_": str(uuid.uuid4())})

def normalize_year_value(val: str) -> str:
    """Extract a 1000–2999 year-like integer from messy input, else return empty."""
    s = str(val or "").strip()
    m = re.search(r"\b(1\d{3}|2\d{3})\b", s)  # 1000-2999
    if m:
        return m.group(1)
    try:
        f = float(s); i = int(f)
        if 1000 <= i <= 2999:
            return str(i)
    except:
        pass
    return ""

def to_int_year_safe(x):
    """Convert year string to sortable int; use very small sentinel when missing."""
    s = normalize_year_value(x)
    try:
        return int(s) if s else -10**9
    except:
        return -10**9

def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure all required columns exist and are ordered; normalize year."""
    if "doi_or_url" not in df.columns and "pdf_link" in df.columns:
        df["doi_or_url"] = df["pdf_link"]
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df["year"] = df["year"].apply(normalize_year_value)
    return df[REQUIRED_COLUMNS]

def save_all(df: pd.DataFrame):
    """Persist to XLSX, CSV, and JSON (always in sync)."""
    df = ensure_columns(df.copy())
    with pd.ExcelWriter(XLSX_PATH, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="papers")
    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(df.to_dict(orient="records"), f, ensure_ascii=False, indent=2)

def load_data() -> pd.DataFrame:
    """Load from CSV (preferred) or JSON fallback; ensure schema and IDs."""
    df = pd.DataFrame(columns=REQUIRED_COLUMNS)
    if os.path.exists(CSV_PATH):
        try:
            df = pd.read_csv(CSV_PATH)
        except Exception as e:
            st.error(f"Error reading CSV: {e}")
    elif os.path.exists(JSON_PATH):
        try:
            with open(JSON_PATH, "r", encoding="utf-8") as f:
                df = pd.DataFrame(json.load(f))
        except Exception as e:
            st.error(f"Error reading JSON: {e}")
    df = ensure_columns(df)
    missing = (df["id"] == "") | (df["id"].isna())
    if missing.any():
        df.loc[missing, "id"] = [str(uuid.uuid4()) for _ in range(missing.sum())]
        save_all(df)
    return df

def make_record(d: dict) -> dict:
    """Build a new canonical record from input dict."""
    return {
        "id": str(uuid.uuid4()),
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "title": d.get("title","").strip(),
        "authors": d.get("authors","").strip(),
        "year": normalize_year_value(d.get("year","")),
        "journal": d.get("journal","").strip(),
        "population": d.get("population","").strip(),
        "main_variables": d.get("main_variables","").strip(),
        "measures": d.get("measures","").strip(),
        "takeaway": d.get("takeaway","").strip(),
        "tags": d.get("tags","").strip(),
        "doi_or_url": d.get("doi_or_url","").strip(),
        "notes": d.get("notes","").strip(),
    }

def idx_by_id(df: pd.DataFrame, rec_id: str):
    """Return integer index for record ID, else None."""
    hit = df.index[df["id"] == rec_id]
    return int(hit[0]) if len(hit) else None

def parse_tags(tag_str: str):
    """Split tags by commas/semicolons/slashes/pipes/whitespace; trim blanks."""
    if not isinstance(tag_str, str):
        return []
    parts = re.split(r"[,\uFF0C;\uFF1B/|]+|\s+", str(tag_str).strip())
    return [p for p in (t.strip() for t in parts) if p]

def color_for_tag(tag: str):
    """Map tag to deterministic background/border color from palettes."""
    if not tag:
        return TAG_COLOR_PALETTE[0], TAG_BORDER_PALETTE[0]
    h = int(hashlib.md5(tag.lower().encode("utf-8")).hexdigest(), 16)
    i = h % len(TAG_COLOR_PALETTE)
    return TAG_COLOR_PALETTE[i], TAG_BORDER_PALETTE[i]

def card_bg_for_tags(tags: list, fallback_idx: int):
    """Pick a pleasant card background influenced by first tag or fallback."""
    if not tags:
        return CARD_BG_FALLBACKS[fallback_idx % len(CARD_BG_FALLBACKS)]
    bg, _ = color_for_tag(tags[0])
    return bg

def tag_chips_html(tags: list):
    """Render small HTML chips for tag list."""
    chips = []
    for t in tags:
        bg, border = color_for_tag(t)
        chips.append(
            f'<span style="display:inline-block;margin:2px 6px 2px 0;padding:2px 8px;'
            f'border:1px solid {border};border-radius:999px;background:{bg};font-size:12px;">{t}</span>'
        )
    return "".join(chips) if chips else '<span style="color:#777">—</span>'

def normalize_text(x):
    """Trim and lowercase a string safely."""
    return (x or "").strip().lower()

def apply_filters(df: pd.DataFrame, q: str, selected_tags: list, mode: str):
    """Apply keyword + tag filters to dataframe."""
    out = ensure_columns(df.copy())
    if q.strip():
        qq = normalize_text(q)
        mask = (
            out["title"].str.lower().str.contains(qq, na=False) |
            out["authors"].str.lower().str.contains(qq, na=False) |
            out["journal"].str.lower().str.contains(qq, na=False) |
            out["population"].str.lower().str.contains(qq, na=False) |
            out["main_variables"].str.lower().str.contains(qq, na=False) |
            out["measures"].str.lower().str.contains(qq, na=False) |
            out["takeaway"].str.lower().str.contains(qq, na=False) |
            out["tags"].str.lower().str.contains(qq, na=False) |
            out["notes"].str.lower().str.contains(qq, na=False) |
            out["doi_or_url"].str.lower().str.contains(qq, na=False)
        )
        out = out[mask]
    if selected_tags:
        target = set(t.lower() for t in selected_tags)
        row_tags = out["tags"].apply(lambda s: set(t.lower() for t in parse_tags(s)))
        if mode == "ALL":
            mask = row_tags.apply(lambda s: target.issubset(s))
        else:
            mask = row_tags.apply(lambda s: len(s & target) > 0)
        out = out[mask]
    return ensure_columns(out)

def apply_sort(df: pd.DataFrame, field: str, ascending: bool):
    """Sort by supported field; year is sorted numerically via helper."""
    df = ensure_columns(df.copy())
    if df.empty:
        return df
    if field == "year":
        return df.assign(_y=df["year"].apply(to_int_year_safe)).sort_values(by="_y", ascending=ascending).drop(columns="_y")
    elif field in df.columns:
        return df.sort_values(by=field, ascending=ascending)
    else:
        return df

def set_filters_to_tag(tag: str):
    """Quickly set filters to a single tag."""
    st.session_state["applied_filters"] = {"q": "", "tags": [tag], "mode": "ANY"}
    hard_rerun()

# -----------------------
# Load data
# -----------------------
df = load_data()

# =========================================================
# (1) Add New Paper — keep all features + clear form + stronger dedupe
# =========================================================
# Use a nonce to force new widget keys after saving, which resets values to empty.
if "new_form_nonce" not in st.session_state:
    st.session_state["new_form_nonce"] = 0
nonce = st.session_state["new_form_nonce"]

st.subheader("Add New Paper (all fields optional)")
st.caption("Tip: move between fields with **Tab** or by clicking; duplicate checks run automatically.")

# Title / Authors
title = st.text_input("Paper Title", key=f"new_title_{nonce}")
authors = st.text_input("Authors (comma separated)", key=f"new_authors_{nonce}")

# Duplicate check: title + authors (case-insensitive, trimmed)
def _norm(s): return str(s or "").strip().lower()
dup_mask = (
    (_norm(title) != "") & (_norm(authors) != "") &
    (df["title"].str.strip().str.lower() == _norm(title)) &
    (df["authors"].str.strip().str.lower() == _norm(authors))
)
dup_exists = dup_mask.any()
if dup_exists:
    st.warning("A note with the same **Title + Authors** already exists. Saving is disabled.")
    # Show first two matches as a hint
    _dups = df.loc[dup_mask, ["title", "authors", "year", "journal"]].head(2)
    for _, r in _dups.iterrows():
        st.caption(f"• {r['title']} — {r['authors']} ({r['year'] or '—'}) | {r['journal'] or '—'}")

col_year, col_journal = st.columns([1, 2])
with col_year:
    year = st.text_input("Year", key=f"new_year_{nonce}")
with col_journal:
    journal = st.text_input("Journal / Conference / Source", key=f"new_journal_{nonce}")

# Population (with hint to use tags for population keywords)
st.markdown("Population")
st.caption("Tip: describe the population in detail here and put population keywords in Tags.")
population = st.text_input("", key=f"new_population_{nonce}", label_visibility="collapsed")

# Variables / Measures / Takeaway
main_variables = st.text_area("Main Variables", key=f"new_variables_{nonce}")
measures = st.text_area("Measures / Methods", key=f"new_measures_{nonce}")
takeaway = st.text_area("Takeaway / Key Points", key=f"new_takeaway_{nonce}")

# Tags (choose existing + add new)
st.markdown("Tags (choose from existing)")
st.caption("Tip: add population keywords (e.g., adolescents, depression) as tags so that you can filter by population.")
tag_col1, tag_col2 = st.columns([3, 2])
with tag_col1:
    existing_tags = sorted({t for s in df["tags"] for t in parse_tags(s)})
    tag_select = st.multiselect("", options=existing_tags, default=[], key=f"new_tag_select_{nonce}",
                                label_visibility="collapsed")
with tag_col2:
    tag_newtext = st.text_input("+ New tags (comma separated)", key=f"new_tag_new_{nonce}")

doi_or_url = st.text_input("DOI or URL", key=f"new_doi_{nonce}")
notes = st.text_area("Additional Notes", key=f"new_notes_{nonce}")

# Save button — disabled when duplicate is detected
save_new = st.button("Save Note", key=f"save_new_{nonce}", disabled=dup_exists)

if save_new:
    # Build and save the new record
    extra_list = [t.strip() for t in re.split(r"[,\uFF0C;\uFF1B/|]+", tag_newtext) if t.strip()] if tag_newtext.strip() else []
    final_tags = sorted(set(tag_select + extra_list), key=lambda x: x.lower())
    tags_str = ", ".join(final_tags)
    d = {
        "title": title,
        "authors": authors,
        "year": year,
        "journal": journal,
        "population": population,
        "main_variables": main_variables,
        "measures": measures,
        "takeaway": takeaway,
        "tags": tags_str,
        "doi_or_url": doi_or_url,
        "notes": notes,
    }
    df = pd.concat([df, pd.DataFrame([make_record(d)])], ignore_index=True)
    save_all(df)

    # Show success, then pause 1 second so the message is visible before refresh
    st.success("Saved! Fields will clear shortly…")
    time.sleep(1)

    # Increment nonce so all 'new_*' widgets get new keys (clean form), then rerun
    st.session_state["new_form_nonce"] = nonce + 1
    st.rerun()

# =========================================================
# (2) Search & Filter / Import & Export (need to Apply)
# =========================================================
with st.expander("🔎 Search & Filter / ⏫ Import & ⏬ Export", expanded=False):
    c1, c2, c3 = st.columns([2, 2, 1.2])
    with c1:
        q_input = st.text_input(
            "Keyword search",
            placeholder="Title, authors, journal, population, variables, takeaway, tags, notes, DOI/URL",
            help="These inputs do NOT apply automatically. Click **Apply filters** below."
        )
    with c2:
        selected_tags_input = st.multiselect(
            "Filter by tags (multi-select)",
            options=existing_tags, default=[],
            help="Pick tags, then click **Apply filters**."
        )
    with c3:
        filter_mode_input = st.radio(
            "Mode", options=["ANY", "ALL"], index=0, horizontal=True,
            help="ANY = match any selected tag; ALL = must contain all selected tags. Click **Apply filters**."
        )

    st.markdown("---")
    # Bulk Import CSV (append + de-dup based on title+authors if present)
    imp_c1, _ = st.columns([2, 2])
    with imp_c1:
        st.markdown("**Bulk Import CSV**")
        file = st.file_uploader("Upload CSV (append; de-dup if title & authors present)", type=["csv"], key="csv_imp")
        if file is not None:
            try:
                imp_df = pd.read_csv(file)
                if "doi_or_url" not in imp_df.columns and "pdf_link" in imp_df.columns:
                    imp_df["doi_or_url"] = imp_df["pdf_link"]
                for col in REQUIRED_COLUMNS:
                    if col not in imp_df.columns:
                        imp_df[col] = ""
                imp_df["year"] = imp_df["year"].apply(normalize_year_value)
                miss = (imp_df["id"] == "") | (imp_df["id"].isna())
                imp_df.loc[miss, "id"] = [str(uuid.uuid4()) for _ in range(miss.sum())]
                def keyfun(row):
                    t = str(row.get("title","")).strip().lower()
                    a = str(row.get("authors","")).strip().lower()
                    return (t, a) if (t and a) else None
                existing_keys = {keyfun(row) for _, row in df.iterrows() if keyfun(row) is not None}
                to_add = []
                for _, row in imp_df.iterrows():
                    k = keyfun(row)
                    if (k is None) or (k not in existing_keys):
                        r = row.to_dict()
                        r["year"] = normalize_year_value(r.get("year",""))
                        to_add.append(r)
                        if k is not None:
                            existing_keys.add(k)
                if to_add:
                    df = pd.concat([df, pd.DataFrame(to_add)], ignore_index=True)
                    save_all(df)
                    st.success(f"Imported {len(to_add)} records. Files auto-updated (Excel/CSV/JSON).")
                    hard_rerun()
                else:
                    st.info("No new records to import (all duplicates).")
            except Exception as e:
                st.error(f"Import failed: {e}")

    # Apply filters button
    st.markdown("---")
    if st.button("Apply filters"):
        st.session_state["applied_filters"] = {
            "q": q_input,
            "tags": selected_tags_input,
            "mode": filter_mode_input,
        }
        st.success("Filters applied. The list & downloads below are updated.")

    # Export current filtered (after Apply)
    st.markdown("---")
    st.markdown("**Export Current Filtered Results** (after Apply)")
    applied = st.session_state.get("applied_filters", {"q": "", "tags": [], "mode": "ANY"})
    filtered_applied_df = apply_filters(df, applied["q"], applied["tags"], applied["mode"])

    def df_to_csv_bytes(df_in: pd.DataFrame) -> bytes:
        buf = io.StringIO()
        ensure_columns(df_in).to_csv(buf, index=False, encoding="utf-8-sig")
        return buf.getvalue().encode("utf-8-sig")

    def df_to_json_bytes(df_in: pd.DataFrame) -> bytes:
        s = json.dumps(ensure_columns(df_in).to_dict(orient="records"), ensure_ascii=False, indent=2)
        return s.encode("utf-8")

    def df_to_xlsx_bytes(df_in: pd.DataFrame) -> bytes:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            ensure_columns(df_in).to_excel(writer, index=False, sheet_name="papers_filtered")
        return output.getvalue()

    ec, cc, jc = st.columns(3)
    with ec:
        st.download_button("Download FILTERED as Excel",
            data=df_to_xlsx_bytes(filtered_applied_df),
            file_name="paper_notes_filtered.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with cc:
        st.download_button("Download FILTERED as CSV",
            data=df_to_csv_bytes(filtered_applied_df),
            file_name="paper_notes_filtered.csv",
            mime="text/csv")
    with jc:
        st.download_button("Download FILTERED as JSON",
            data=df_to_json_bytes(filtered_applied_df),
            file_name="paper_notes_filtered.json",
            mime="application/json")

# =========================================================
# (3) Saved Papers — sort & compact view
# =========================================================
applied = st.session_state.get("applied_filters", {"q": "", "tags": [], "mode": "ANY"})
filtered_df = apply_filters(df, applied["q"], applied["tags"], applied["mode"])

st.markdown("---")
st.subheader(f"📄 Saved Papers — Showing {len(filtered_df)} of {len(df)}")
st.caption(
    f"Auto backups: **Excel** `{XLSX_PATH}` → **CSV** `{CSV_PATH}` → **JSON** `{JSON_PATH}` (always up-to-date)"
)

sc1, sc2, sc3 = st.columns([2.2, 1.2, 1.2])
with sc1:
    sort_field = st.selectbox(
        "Sort by",
        options=[("saved_at", "Saved time"), ("year", "Year"), ("authors", "Authors"), ("title", "Title")],
        index=0, format_func=lambda x: x[1]
    )[0]
with sc2:
    sort_order = st.radio("Order", options=["Descending", "Ascending"], index=0, horizontal=True)
with sc3:
    st.markdown("&nbsp;", unsafe_allow_html=True)
    compact_view = st.toggle("Compact View", value=True, help="Show essentials only; turn off to show more fields.")

ascending = (sort_order == "Ascending")
filtered_df = apply_sort(filtered_df, sort_field, ascending)

view_mode = st.radio(
    "View mode",
    ["Cards", "Grouped by Year", "Grouped by Author", "Grouped by Journal", "Grouped by Tag"],
    horizontal=True, index=0
)

# ---------- renderer ----------
def render_card(row, i, key_prefix: str):
    tags_list = parse_tags(row["tags"])
    card_bg = card_bg_for_tags(tags_list, i)
    chips_html = tag_chips_html(tags_list)

    essentials_html = (
        f"<p style='margin:2px 0'><b>👤 Authors:</b> {row['authors']}</p>"
        f"<p style='margin:2px 0'><b>📅 Year:</b> {normalize_year_value(row['year'])}</p>"
        f"<p style='margin:2px 0'><b>🏛 Journal:</b> {row['journal']}</p>"
        f"<p style='margin:2px 0'><b>🧑‍🤝‍🧑 Population:</b> {row['population']}</p>"
        f"<p style='margin:2px 0'><b>📝 Takeaway:</b> {row['takeaway']}</p>"
    )
    more_html = (
        f"<p style='margin:2px 0'><b>🔬 Variables:</b> {row['main_variables']}</p>"
        f"<p style='margin:2px 0'><b>🧪 Measures:</b> {row['measures']}</p>"
        f"<p style='margin:2px 0'><b>🔗 DOI/URL:</b> {row['doi_or_url'] or '—'}</p>"
        f"<p style='margin:2px 0'><b>🗒 Notes:</b> {row['notes'] or '—'}</p>"
    )

    st.markdown(
        f"""
        <div style="
            border:1px solid #ddd; 
            border-radius:12px; 
            padding:12px; 
            margin-bottom:12px;
            background:{card_bg};
            box-shadow: 2px 2px 8px rgba(0,0,0,0.08);
        ">
            <h4 style="margin:0 0 6px 0;">📖 {row['title'] or '(Untitled)'}</h4>
            {essentials_html if compact_view else essentials_html + more_html}
            <div style="margin:6px 0 4px 0">{chips_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if compact_view:
        with st.expander("Show more", expanded=False):
            st.markdown(more_html, unsafe_allow_html=True)

    rec_id = row["id"]
    b1, b2, b3 = st.columns([1, 1, 1])
    with b1:
        if st.button("Edit", key=f"{key_prefix}_edit_{rec_id}"):
            st.session_state[f"editing_{rec_id}"] = True
    with b2:
        confirm_key = f"{key_prefix}_confirm_{rec_id}"
        confirm_delete = st.checkbox("❗️confirm delete", key=confirm_key, value=st.session_state.get(confirm_key, False))
    with b3:
        if st.button("Delete", key=f"{key_prefix}_delete_{rec_id}", disabled=not confirm_delete):
            real_idx = idx_by_id(df, rec_id)
            if real_idx is not None and st.session_state.get(confirm_key, True):
                dfn = df.drop(index=real_idx).reset_index(drop=True)
                save_all(dfn)
                st.success("Deleted. Reloading...")
                time.sleep(0.6)
                for k in list(st.session_state.keys()):
                    if k.endswith(f"_confirm_{rec_id}") or k == f"editing_{rec_id}":
                        st.session_state.pop(k, None)
                hard_rerun()

    if st.session_state.get(f"editing_{rec_id}", False):
        with st.expander("Editing...", expanded=True):
            real_idx = idx_by_id(df, rec_id)
            if real_idx is None:
                st.info("This item was removed.")
                st.session_state.pop(f"editing_{rec_id}", None)
            else:
                current = df.loc[real_idx].copy()

                e1, e2 = st.columns([3, 2])
                with e1:
                    new_title = st.text_input("Paper Title", current["title"], key=f"{key_prefix}_edit_title_{rec_id}")
                with e2:
                    new_year = st.text_input("Year", current["year"], key=f"{key_prefix}_edit_year_{rec_id}")

                new_authors = st.text_input("Authors", current["authors"], key=f"{key_prefix}_edit_authors_{rec_id}")
                new_journal = st.text_input("Journal / Conference / Source", current["journal"], key=f"{key_prefix}_edit_journal_{rec_id}")

                # Population hint
                st.markdown("**Population**")
                st.caption("Tip: describe the population; put keywords in Tags.")
                new_population = st.text_input("", current["population"],
                                               key=f"{key_prefix}_edit_population_{rec_id}",
                                               label_visibility="collapsed")

                new_variables = st.text_area("Main Variables", current["main_variables"], key=f"{key_prefix}_edit_variables_{rec_id}")
                new_measures = st.text_area("Measures / Methods", current["measures"], key=f"{key_prefix}_edit_measures_{rec_id}")
                new_takeaway = st.text_area("Takeaway / Key Points", current["takeaway"], key=f"{key_prefix}_edit_takeaway_{rec_id}")

                # Tags editor (existing + extra)
                st.markdown("**Tags (autocomplete from existing)**")
                st.caption("Tip: add population keywords (e.g., adolescents, depression) as tags so that you can filter by population.")
                tagc1, tagc2 = st.columns([3, 2])
                with tagc1:
                    all_existing = sorted({t for s in df["tags"] for t in parse_tags(s)})
                    cur_tag_list = parse_tags(current["tags"])
                    sel_tags = st.multiselect("", options=all_existing, default=cur_tag_list,
                                              key=f"{key_prefix}_edit_tag_sel_{rec_id}",
                                              label_visibility="collapsed")
                with tagc2:
                    extra_tags_str = st.text_input("+ New tags (comma separated)", "",
                                                   key=f"{key_prefix}_edit_tag_extra_{rec_id}")

                new_doi = st.text_input("DOI or URL", current["doi_or_url"], key=f"{key_prefix}_edit_doi_{rec_id}")
                new_notes = st.text_area("Additional Notes", current["notes"], key=f"{key_prefix}_edit_notes_{rec_id}")

                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Save Changes", key=f"{key_prefix}_save_edit_{rec_id}"):
                        extra_list = [t.strip() for t in re.split(r"[,\uFF0C;\uFF1B/|]+", extra_tags_str) if t.strip()] if extra_tags_str.strip() else []
                        final_tags = sorted(set(sel_tags + extra_list), key=lambda x: x.lower())
                        df.loc[real_idx] = {
                            "id": rec_id,
                            "saved_at": datetime.now().isoformat(timespec="seconds"),
                            "title": new_title,
                            "authors": new_authors,
                            "year": normalize_year_value(new_year),
                            "journal": new_journal,
                            "population": new_population,
                            "main_variables": new_variables,
                            "measures": new_measures,
                            "takeaway": new_takeaway,
                            "tags": ", ".join(final_tags),
                            "doi_or_url": new_doi,
                            "notes": new_notes,
                        }
                        save_all(df)
                        st.success("Changes saved! Reloading...")
                        time.sleep(1)
                        st.session_state[f"editing_{rec_id}"] = False
                        hard_rerun()
                with c2:
                    if st.button("Cancel", key=f"{key_prefix}_cancel_edit_{rec_id}"):
                        st.session_state[f"editing_{rec_id}"] = False
                        hard_rerun()

# ----------------------- render views -----------------------
if filtered_df.empty:
    st.info("No notes match. Try **Apply filters** with different settings.")
else:
    if view_mode == "Cards":
        num_cols = 3
        cols = st.columns(num_cols)
        for i, row in filtered_df.reset_index(drop=True).iterrows():
            with cols[i % num_cols]:
                render_card(row, i, key_prefix="cards")

    elif view_mode == "Grouped by Year":
        grouped = filtered_df.copy()
        grouped["_y"] = grouped["year"].apply(to_int_year_safe)
        grouped = grouped.sort_values(by=["_y","saved_at"], ascending=[False, False])
        for yr, g in grouped.groupby("_y", sort=False):
            label = "Unknown" if (yr == -10**9) else str(yr)
            with st.expander(f"📅 Year: {label} ({len(g)})", expanded=False):
                cols = st.columns(3)
                for i, row in g.reset_index(drop=True).iterrows():
                    with cols[i % 3]:
                        render_card(row, i, key_prefix=f"year_{label}")

    elif view_mode == "Grouped by Author":
        def split_authors(s):
            return [a.strip() for a in str(s).split(",") if a.strip()]
        exploded = []
        for _, r in filtered_df.iterrows():
            lst = split_authors(r["authors"]) or ["Unknown"]
            for a in lst:
                rr = r.copy()
                rr["__author_group"] = a
                exploded.append(rr)
        if exploded:
            gdf = pd.DataFrame(exploded).sort_values(by=["__author_group","saved_at"], ascending=[True, False])
            for author, g in gdf.groupby("__author_group", sort=True):
                with st.expander(f"👤 Author: {author} ({len(g)})", expanded=False):
                    cols = st.columns(3)
                    for i, row in g.reset_index(drop=True).iterrows():
                        with cols[i % 3]:
                            render_card(row, i, key_prefix=f"author_{author.replace(' ','_')}")

    elif view_mode == "Grouped by Journal":
        def norm_j(s):
            if s is None or (isinstance(s, float) and (math.isnan(s))):
                return "Unknown"
            x = str(s).strip()
            return x if x and x.lower() != "nan" else "Unknown"
        grouped = filtered_df.copy()
        grouped["__journal"] = grouped["journal"].apply(norm_j)
        grouped = grouped.sort_values(by=["__journal","saved_at"], ascending=[True, False])
        for jn, g in grouped.groupby("__journal", sort=True):
            with st.expander(f"🏛 Journal: {jn} ({len(g)})", expanded=False):
                cols = st.columns(3)
                for i, row in g.reset_index(drop=True).iterrows():
                    with cols[i % 3]:
                        render_card(row, i, key_prefix=f"journal_{jn.replace(' ','_')}")

    else:  # Grouped by Tag
        colA, colB = st.columns([1, 2])
        with colA:
            top_n = st.number_input("Top N tags", min_value=5, max_value=200, value=30, step=5)
        with colB:
            tag_query = st.text_input("Filter tag names (optional)", placeholder="Type to filter tag groups")

        all_pairs = []
        for _, r in filtered_df.iterrows():
            lst = parse_tags(r["tags"])
            if not lst:
                all_pairs.append(("(No tag)", r))
            else:
                for t in lst:
                    all_pairs.append((t, r))

        if all_pairs:
            cnt = Counter([t for t, _ in all_pairs])
            tags_sorted = sorted(cnt.keys(), key=lambda k: (-cnt[k], k.lower()))
            if tag_query.strip():
                q = tag_query.strip().lower()
                tags_sorted = [t for t in tags_sorted if q in t.lower()]
            tags_sorted = tags_sorted[:top_n]

            for tg in tags_sorted:
                rows = [r for (t, r) in all_pairs if t == tg]
                with st.expander(f"🏷 Tag: {tg} ({len(rows)})", expanded=False):
                    cols = st.columns(3)
                    for i, row in pd.DataFrame(rows).reset_index(drop=True).iterrows():
                        with cols[i % 3]:
                            render_card(row, i, key_prefix=f"tag_{tg.replace(' ','_')}")
        else:
            st.info("No tags to group.")

# =========================================================
# Tag Stats & Fancy Tag Cloud (HTML/CSS) + Clickable Chips
# =========================================================
st.markdown("---")
st.subheader("🏷 Tag Statistics & Cloud (based on **applied** filters)")

tag_counter = Counter()
for tags in filtered_df["tags"]:
    for t in parse_tags(tags):
        tag_counter[t] += 1

if not tag_counter:
    st.info("No tags to show. Add tags or change filters.")
else:
    top_items = tag_counter.most_common(20)
    if top_items:
        df_top = pd.DataFrame(top_items, columns=["tag", "count"]).set_index("tag")
        st.bar_chart(df_top)

    max_cnt = max(tag_counter.values())
    cloud_html = []
    for tag, cnt in tag_counter.items():
        size = 14 + int(24 * cnt / max_cnt)
        h = int(hashlib.md5(tag.lower().encode("utf-8")).hexdigest(), 16)
        angle = (h % 21) - 10
        op = 0.55 + 0.45 * (cnt / max_cnt)
        bg, border = color_for_tag(tag)
        shadow = f"0 0 {max(2,int(size*0.05))}px rgba(0,0,0,{0.15 + 0.25*(cnt/max_cnt):.2f})"
        cloud_html.append(
            f'<span class="tg" style="font-size:{size}px; transform:rotate({angle}deg); '
            f'opacity:{op:.2f}; border:1px solid {border}; background:{bg}; '
            f'padding:4px 10px; margin:8px; display:inline-block; border-radius:999px; '
            f'text-shadow:{shadow};">{tag}</span>'
        )
    cloud_style = """
    <style>
      .tg { transition: transform .12s ease, box-shadow .12s ease; }
      .tg:hover { transform: scale(1.06) rotate(0deg); box-shadow: 0 6px 16px rgba(0,0,0,.18); }
      .cloud-wrap { line-height: 2.0; }
    </style>
    """
    st.markdown(cloud_style + "<div class='cloud-wrap'>" + "".join(cloud_html) + "</div>", unsafe_allow_html=True)

    st.markdown("**Quick filter by tag (click a chip):**")
    top_click = [t for t, _ in tag_counter.most_common(30)]
    chip_cols = st.columns(6)
    for i, t in enumerate(top_click):
        with chip_cols[i % 6]:
            if st.button(t, key=f"click_tag_{t}"):
                set_filters_to_tag(t)

# =========================================================
# Full Export / Backup (All Records) — auto-updated on any change
# =========================================================
st.markdown("---")
st.subheader("Full Export / Backup (All Records)")
st.caption(
    f"No extra buttons here: the app **automatically keeps** these files up-to-date after every add/edit/delete/import:\n"
    f"1) **Excel**: `{XLSX_PATH}`\n"
    f"2) **CSV**: `{CSV_PATH}`\n"
    f"3) **JSON**: `{JSON_PATH}`"
)
