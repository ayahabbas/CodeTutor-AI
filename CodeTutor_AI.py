import io
import sys
import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="CodeTutor AI", page_icon="⚡", layout="wide")

st.markdown('''<style>.stApp { background-color: #0b0e14; color: #e6edf3; }</style>''', unsafe_allow_html=True)

defaults = {"score": 0, "streak": 0, "hints": [], "buggy_code": "", "test_cases": "", "solved": False, "trace_logs": [], "complexity": None}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

st.sidebar.title("⚡ CodeTutor AI")
st.sidebar.caption("Socratic Debugging & AST Runtime Analytics")

col_s1, col_s2 = st.sidebar.columns(2)
col_s1.metric("XP Score 🏆", st.session_state.score)
col_s2.metric("Streak 🔥", st.session_state.streak)

api_key = st.sidebar.text_input("🔑 Gemini API Key", type="password")
selected_model_name = st.sidebar.selectbox("AI Brain Core", ["gemini-2.5-flash", "gemini-2.5-pro"])

def run_code_with_trace(code_str):
    logs = []
    buffer = io.StringIO()
    def tracer(frame, event, arg):
        if event == "line":
            if frame.f_code.co_filename == "<string>":
                logs.append({"line": frame.f_lineno, "locals": {k: repr(v) for k, v in frame.f_locals.items() if not k.startswith("__")}})
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
    st.info("👈 Enter your Gemini API key in the sidebar.")
else:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(selected_model_name)

    col_ctrl1, col_ctrl2 = st.columns([3, 1])
    with col_ctrl1:
        difficulty = st.select_slider("Select Tier:", options=["Junior", "Mid", "Senior"])
    with col_ctrl2:
        if st.button("🎲 Generate Challenge", use_container_width=True):
            st.session_state.hints = []
            st.session_state.solved = False
            st.session_state.trace_logs = []
            st.session_state.complexity = None
            gen_prompt = f"Create a Python challenge for {difficulty}. Format strict:\n---CODE---\n<code_with_bug>\n---TESTS---\n<asserts>"
            res = model.generate_content(gen_prompt)
            raw = res.text
            st.session_state.buggy_code = raw.split("---CODE---")[1].split("---TESTS---")[0].strip().replace("```python", "").replace("```", "")
            st.session_state.test_cases = raw.split("---TESTS---")[1].strip().replace("```python", "").replace("```", "")

    if st.session_state.buggy_code:
        left_col, right_col = st.columns([3, 2])
        with left_col:
            edited_code = st.text_area("Editor:", value=st.session_state.buggy_code, height=350)
            c_btn1, c_btn2, c_btn3 = st.columns(3)
            if c_btn1.button("▶️ Run"):
                stdout, err, logs = run_code_with_trace(edited_code)
                st.session_state.trace_logs = logs
                if err: st.error(err)
                else: st.code(stdout)
            if c_btn2.button("🧪 Tests"):
                stdout, err, logs = run_code_with_trace(f"{edited_code}\n\n{st.session_state.test_cases}")
                st.session_state.trace_logs = logs
                if err: st.error(err)
                else:
                    st.success("Passed!")
                    if not st.session_state.solved:
                        st.session_state.score += 25
                        st.session_state.solved = True
                        st.session_state.complexity = model.generate_content(f"Analyze complexity:\n{edited_code}").text
            if c_btn3.button("🔓 Solution"):
                st.markdown(model.generate_content(f"Fix and explain:\n{st.session_state.buggy_code}").text)
        with right_col:
            tab_ai, tab_ast, tab_perf = st.tabs(["💬 AI", "🔍 Trace", "📊 Complexity"])
            with tab_ai:
                if st.button("💡 Hint"):
                    hint = model.generate_content(f"Give Socratic hint for:\n{edited_code}").text
                    st.session_state.hints.append(hint)
                for h in st.session_state.hints: st.info(h)
            with tab_ast:
                if st.session_state.trace_logs:
                    step = st.slider("Step", 0, len(st.session_state.trace_logs)-1, 0)
                    st.json(st.session_state.trace_logs[step])
            with tab_perf:
                if st.session_state.complexity: st.write(st.session_state.complexity)
