import io
import sys
import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="CodeTutor AI", page_icon="⚡", layout="wide")

st.markdown('''<style>.stApp { background-color: #0b0e14; color: #e6edf3; }</style>''', unsafe_allow_html=True)

defaults = {
    "score": 0, 
    "streak": 0, 
    "hints": [], 
    "buggy_code": "", 
    "test_cases": "", 
    "solved": False, 
    "trace_logs": [], 
    "complexity": None
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

st.sidebar.title("⚡ CodeTutor AI")
st.sidebar.caption("Socratic Debugging & AST Runtime Analytics")

col_s1, col_s2 = st.sidebar.columns(2)
col_s1.metric("XP Score 🏆", st.session_state.score)
col_s2.metric("Streak 🔥", st.session_state.streak)

api_key = st.sidebar.text_input("🔑 Gemini API Key", type="password")
selected_model = st.sidebar.selectbox("AI Brain Core", ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"])

def run_code_with_trace(code_str):
    logs = []
    buffer = io.StringIO()
    def tracer(frame, event, arg):
        if event == "line":
            if frame.f_code.co_filename == "<string>":
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

st.title("🎓 CodeTutor AI")

if not api_key:
    st.info("👈 Please enter your Gemini API key in the left sidebar to start.")
else:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(selected_model)

    col_ctrl1, col_ctrl2 = st.columns([3, 1])
    with col_ctrl1:
        difficulty = st.select_slider("Select Difficulty Tier:", options=["Junior", "Mid", "Senior"])
    with col_ctrl2:
        if st.button("🎲 Generate Challenge", use_container_width=True):
            st.session_state.hints = []
            st.session_state.solved = False
            st.session_state.trace_logs = []
            st.session_state.complexity = None
            
            prompt = (
                f"Create a Python coding challenge suitable for a {difficulty} level student. "
                "Include a deliberate bug in the code. "
                "Return output using EXACT format:\n"
                "---CODE---\n<python_code_with_bug>\n"
                "---TESTS---\n<assert_statements>"
            )
            with st.spinner("Generating challenge..."):
                try:
                    res = model.generate_content(prompt)
                    raw = res.text
                    if "---CODE---" in raw and "---TESTS---" in raw:
                        st.session_state.buggy_code = raw.split("---CODE---")[1].split("---TESTS---")[0].strip().replace("```python", "").replace("```", "")
                        st.session_state.test_cases = raw.split("---TESTS---")[1].strip().replace("```python", "").replace("```", "")
                    else:
                        st.error("Failed to parse challenge format. Please click 'Generate Challenge' again.")
                except Exception as ex:
                    st.error(f"API Error: {ex}")

    if st.session_state.buggy_code:
        left_col, right_col = st.columns([3, 2])
        
        with left_col:
            edited_code = st.text_area("Editor:", value=st.session_state.buggy_code, height=350)
            c_btn1, c_btn2, c_btn3 = st.columns(3)
            
            if c_btn1.button("▶️ Run Code"):
                stdout, err, logs = run_code_with_trace(edited_code)
                st.session_state.trace_logs = logs
                if err: 
                    st.error(err)
                else: 
                    st.code(stdout if stdout else "Code executed successfully (no stdout).")
                    
            if c_btn2.button("🧪 Run Tests"):
                stdout, err, logs = run_code_with_trace(f"{edited_code}\n\n{st.session_state.test_cases}")
                st.session_state.trace_logs = logs
                if err: 
                    st.error(f"Test Failed: {err}")
                else:
                    st.success("All tests passed! 🎉 (+25 XP)")
                    if not st.session_state.solved:
                        st.session_state.score += 25
                        st.session_state.solved = True
                        with st.spinner("Analyzing complexity..."):
                            st.session_state.complexity = model.generate_content(f"Provide Big-O time and space complexity breakdown for:\n{edited_code}").text
                            
            if c_btn3.button("🔓 Solution"):
                with st.spinner("Fetching solution..."):
                    solution_text = model.generate_content(f"Fix the bug and explain the solution:\n{st.session_state.buggy_code}").text
                    st.markdown(solution_text)

        with right_col:
            tab_ai, tab_ast, tab_perf = st.tabs(["💬 AI Tutor", "🔍 Variable Trace", "📊 Complexity"])
            
            with tab_ai:
                if st.button("💡 Socratic Hint"):
                    with st.spinner("Thinking..."):
                        hint = model.generate_content(f"Give a single Socratic hint for this buggy code. Do not give the code fix:\n{edited_code}").text
                        st.session_state.hints.append(hint)
                for h in st.session_state.hints: 
                    st.info(h)
                    
            with tab_ast:
                if st.session_state.trace_logs:
                    step = st.slider("Step", 0, len(st.session_state.trace_logs)-1, 0)
                    st.write(f"**Line Number:** `{st.session_state.trace_logs[step]['line']}`")
                    st.json(st.session_state.trace_logs[step]['locals'])
                else:
                    st.write("Run the code to populate AST execution steps.")
                    
            with tab_perf:
                if st.session_state.complexity: 
                    st.markdown(st.session_state.complexity)
                else:
                    st.write("Pass all unit tests to unlock complexity analysis.")
