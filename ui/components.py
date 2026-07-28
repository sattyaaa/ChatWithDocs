import streamlit as st

def render_sources_badges(sources: list[dict], key_prefix: str):
    """
    Renders source chunks as a horizontal row of small st.buttons with markdown tooltips.
    """
    if not sources:
        return
    
    st.caption("🔍 **Retrieved Context Chunks (Hover to view content):**")
    cols = st.columns(len(sources))
    for idx, doc in enumerate(sources):
        fname = doc.get("filename", "Unknown file")
        page = doc.get("page")
        content = doc.get("content", "")
        
        page_label = f"P. {page + 1}" if page is not None else f"Src {idx + 1}"
        tooltip_text = f"**Source {idx + 1}**\n\n**File:** {fname}\n\n**Page:** {page + 1 if page is not None else 'N/A'}\n\n**Content:**\n{content}"
        
        with cols[idx]:
            st.button(
                label=page_label,
                help=tooltip_text,
                key=f"{key_prefix}_{idx}",
                use_container_width=True
            )
