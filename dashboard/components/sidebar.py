import streamlit as st

from database.queries import create_exam, get_all_exams, get_exam_by_id


def render_sidebar() -> str:
    """Render app navigation and exam selection in the Streamlit sidebar."""
    st.sidebar.title("PHF OMR")
    exams = get_all_exams()
    if exams:
        labels = [exam["name"] for exam in exams]
        current = _current_exam_index(exams)
        selected = st.sidebar.selectbox("Exam", labels, index=current)
        st.session_state["exam_id"] = int(exams[labels.index(selected)]["id"])
        exam = get_exam_by_id(st.session_state["exam_id"])
        st.sidebar.caption(f"Selected: {exam['name'] if exam else selected}")
    else:
        st.sidebar.info("Create an exam to begin.")
        st.session_state.pop("exam_id", None)
    with st.sidebar.expander("New Exam"):
        name = st.text_input("Exam name")
        if st.button("Create Exam", width="stretch") and name.strip():
            st.session_state["exam_id"] = create_exam(name.strip())
            st.rerun()
    return st.sidebar.radio("Navigate", ["Home", "Upload", "Answer Keys", "Results", "Export"])


def _current_exam_index(exams: list[dict]) -> int:
    """Return the selectbox index for the session exam."""
    current_id = st.session_state.get("exam_id")
    for index, exam in enumerate(exams):
        if exam["id"] == current_id:
            return index
    return 0
