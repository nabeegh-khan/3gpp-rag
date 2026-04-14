import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="3GPP Spec Assistant",
    page_icon="📡",
    layout="centered"
)

st.title("📡 3GPP Specification Assistant")
st.caption("Query 3GPP Release 18/19 specifications using natural language. Answers are grounded in the source documents with page citations.")

# check if the API is running
try:
    health = requests.get(f"{API_URL}/health", timeout=3)
    if health.json().get("chain_loaded"):
        st.success("API connected — RAG chain loaded", icon="✅")
    else:
        st.error("API connected but RAG chain not loaded")
except Exception:
    st.error("Cannot connect to API. Make sure the FastAPI server is running on port 8000.")
    st.stop()

st.divider()

# initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# chat input
if prompt := st.chat_input("Ask a question about 3GPP specifications..."):

    # add user message to history and display it
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # call the API and display the response
    with st.chat_message("assistant"):
        with st.spinner("Searching specifications..."):
            try:
                response = requests.post(
                    f"{API_URL}/query",
                    json={"question": prompt},
                    timeout=30
                )
                answer = response.json().get("answer", "No answer returned")
            except Exception as e:
                answer = f"Error contacting API: {str(e)}"

        st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})