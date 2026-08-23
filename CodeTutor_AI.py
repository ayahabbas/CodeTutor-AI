import io
import sys
import streamlit as st
import google.generativeai as genai

# Page Config
st.set_page_config(
    page_title="CodeTutor AI | Socratic Debugging Arena",
    page_icon="⚡",
    layout="wide"
)

st.markdown("""
<style>
    .stApp { background-color: #0b0e14; color: #e6edf3; }
    .metric-card {
        background: linear-gradient(135deg, #161b22 0%, #1f242d 100%);
        border: 1px solid #30363d; border-radius: 12px; padding: 15px; text-align: center;
    }
    .stButton>button {
        border-radius: 8px; font-weight: 600; background: #238636; color: white; border: none;
    }
    .stButton>button:hover { background: #2ea043; }
</style>
""", unsafe_allow_html=True)

# Session State
defaults = {
    "score": 0, "streak": 0, "hints": [], "buggy_code": "",
    "test_cases": "", "solved": False, "trace_logs": [], "complexity": None
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# Sidebar
st.sidebar.title("⚡ CodeTutor AI")
st.sidebar.caption("Socratic Debugging & AST Runtime Analytics")

col_s1, col_s2 = st.sidebar.columns(2)
col_s1.metric("XP Score 🏆", st.session_state.score)
col_s2.metric("Streak 🔥", st.session_state.streak)

api_key = st.sidebar.text_input("🔑 Gemini API Key", type="password")
selected_model = st.sidebar.selectbox("AI Brain Core", ["gemini-2.5-flash", "gemini-2.5-pro"])

# Code Tracer
def run_code_with_trace(code_str):
    logs = []
    buffer = io.StringIO()
    
    def tracer(frame, event, arg):
        if event == "line":
            filename = frame.f_code.co_filename
            if filename == "<string>":
                logs.append({
                    "line": frame.f_lineno,
                    "locals": {k: repr(v) for k, v in frame.f_locals.items() if not k.startswith("__")}
                })
        return tracer

    sys.stdout = buffer
    sys.settrace(tracer)
    try:
        exec(code_str, {})
        output = buffer.getvalue()
        error = None
    except Exception as e:
        output = buffer.getvalue()
        error = f"{type(e).__name__}: {str(e)}"
    finally:
        sys.settrace(None)
        sys.stdout = sys.__stdout__
        
    return output, error, logs

# Main UI
st.title("🎓 CodeTutor AI")
st.caption("AI-Powered Pedagogical Sandbox with Variable-Trace Time Travel & Complexity Profiling")

if not api_key:
    st.info("👈 Enter your Gemini API key in the sidebar to power the Socratic AI Engine.")
else:
    genai.configure(api_key=api_key)

    # Generator
    with st.container():
        col_ctrl1, col_ctrl2 = st.columns([3, 1])
        with col_ctrl1:
            difficulty = st.select_slider(
                "Select Engineering Tier:",
                options=["Junior (Syntax/Off-by-One)", "Mid (Logic/Edge Cases)", "Senior (Algorithmic Mutants)"]
            )
        with col_ctrl2:
            st.write(" ")
            if st.button("🎲 Generate Challenge", use_container_width=True):
                st.session_state.hints = []
                st.session_state.solved = False
                st.session_state.trace_logs = []
                st.session_state.complexity = None
                
                gen_prompt = f"""
                Create a Python coding challenge for {difficulty} level.
                Provide raw Python code with exactly ONE subtle bug injected.
                Include 2 test assertions at the bottom (e.g. `assert function_name(args) == expected`).
                
                Respond in this strict format:
                ---CODE---
                <python_code_with_bug>
                ---TESTS---
                <assert_statements>
                """
                with st.spinner("Injecting bug & generating unit tests..."):
                    res = client.models.generate_content(
                        model=selected_model,
                        contents=gen_prompt
                    )
                    raw = res.text
                    code_part = raw.split("---CODE---")[1].split("---TESTS---")[0].strip()
                    test_part = raw.split("---TESTS---")[1].strip()
                    st.session_state.buggy_code = code_part.replace("```python", "").replace("```", "")
                    st.session_state.test_cases = test_part.replace("```python", "").replace("```", "")

    # Workspace
    if st.session_state.buggy_code:
        left_col, right_col = st.columns([3, 2])

        with left_col:
            st.subheader("💻 IDE Sandbox")
            
            edited_code = st.text_area(
                "Code Editor:",
                value=st.session_state.buggy_code,
                height=350
            )

            c_btn1, c_btn2, c_btn3 = st.columns(3)
            run_btn = c_btn1.button("▶️ Execute Code", use_container_width=True)
            test_btn = c_btn2.button("🧪 Run Unit Tests", use_container_width=True)
            solution_btn = c_btn3.button("🔓 Solution", use_container_width=True)

            # Execution
            if run_btn:
                stdout, err, logs = run_code_with_trace(edited_code)
                st.session_state.trace_logs = logs
                
                if err:
                    st.error(f"Execution Error: {err}")
                else:
                    st.success("Execution Output:")
                    st.code(stdout if stdout else "[No Standard Output]")

            # Unit Tests
            if test_btn:
                full_test_script = f"{edited_code}\n\n{st.session_state.test_cases}"
                stdout, err, logs = run_code_with_trace(full_test_script)
                st.session_state.trace_logs = logs
                
                if err:
                    st.error("❌ Unit Tests Failed!")
                    st.code(err)
                else:
                    st.success("🎉 All Unit Tests Passed!")
                    if not st.session_state.solved:
                        st.session_state.score += 25
                        st.session_state.streak += 1
                        st.session_state.solved = True
                        st.balloons()
                        
                        comp_prompt = f"Analyze time and space complexity for this fixed code:\n{edited_code}. Return a brief summary."
                        comp_res = client.models.generate_content(model=selected_model, contents=comp_prompt)
                        st.session_state.complexity = comp_res.text

            if solution_btn:
                st.warning("Revealing solution reduces current streak.")
                st.session_state.streak = 0
                sol_prompt = f"Fix this code and explain the exact bug in 2 sentences:\n{st.session_state.buggy_code}"
                sol_res = client.models.generate_content(model=selected_model, contents=sol_prompt)
                st.markdown(sol_res.text)

        # AI Sidepanel
        with right_col:
            st.subheader("🧠 Socratic AI & Runtime Insights")
            
            tab_ai, tab_ast, tab_perf = st.tabs(["💬 CodeTutor AI", "🔍 Variable AST Trace", "📊 Complexity Radar"])

            with tab_ai:
                if st.button("💡 Ask CodeTutor AI", use_container_width=True):
                    socratic_sys = """You are CodeTutor AI, a Socratic Code Tutor. Never give away the fix or exact line.
                    Ask a single targeted guiding question to make the student think about their state management or logic."""
                    
                    hint_res = client.models.generate_content(
                        model=selected_model,
                        contents=f"Code:\n{edited_code}\nProvide a Socratic hint.",
                        config=genai.types.GenerateContentConfig(system_instruction=socratic_sys)
                    )
                    st.session_state.hints.append(hint_res.text)

                for i, h in enumerate(st.session_state.hints, 1):
                    st.info(f"**Guide Question {i}:** {h}")

            with tab_ast:
                st.caption("Frame-by-Frame Execution Variable States")
                if st.session_state.trace_logs:
                    step = st.slider("Execution Step Timeline", 0, len(st.session_state.trace_logs)-1, 0)
                    state = st.session_state.trace_logs[step]
                    st.markdown(f"**Line executed:** `{state['line']}`")
                    st.json(state['locals'])
                else:
                    st.caption("Run code or test suite to inspect local variable state transitions.")

            with tab_perf:
                if st.session_state.complexity:
                    st.markdown("### Algorithmic Efficiency")
                    st.success(st.session_state.complexity)
                else:
                    st.caption("Pass all unit tests to unlock Big-O profiling analysis.")
