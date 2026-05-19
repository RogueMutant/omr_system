import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st


def render_results_table(df: pd.DataFrame) -> None:
    """Render a percentage-coloured results table."""
    def color_percentage(value: float) -> str:
        if value >= 70:
            return "background-color: #d7f5dd"
        if value >= 50:
            return "background-color: #ffe8bf"
        return "background-color: #ffd6d6"

    st.dataframe(df.style.map(color_percentage, subset=["percentage"]), width="stretch")


def render_question_stats(stats: dict) -> None:
    """Render per-question correctness percentages with red low-performing bars."""
    questions = sorted(stats.keys())
    percentages = [
        (stats[q]["correct_count"] / stats[q]["total"] * 100) if stats[q]["total"] else 0
        for q in questions
    ]
    colors = ["#c62828" if value < 40 else "#2e7d32" for value in percentages]
    fig, ax = plt.subplots(figsize=(14, 4))
    ax.bar(questions, percentages, color=colors)
    ax.set_xlabel("Question")
    ax.set_ylabel("% correct")
    ax.set_ylim(0, 100)
    st.pyplot(fig)
