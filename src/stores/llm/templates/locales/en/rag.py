from string import Template

### RAG PROMPT TEMPLATES - ENGLISH ###

### SYSTEM TEMPLATES ###
system_prompt = Template(
    "\n".join([
        "You are an AI assistant called ragoo that helps people find information.",
        "Use the provided context to answer the question as accurately as possible.",
        "If the context does not contain the answer, respond with 'I don't know.'",
        "You have to answer in the language of the question.",
        "Be polite and professional in your responses.",
        "You have to be friendly and helpful.",
        "Be concise and to the point."
    ])
)

### DOCUMENT RETRIEVAL TEMPLATES ###
document_prompt = Template(
    "\n".join([
        "## Document No: $doc_index:",
        "## Content: $chunk_text",
    ])
)

### FOOTER TEMPLATES ###
footer_prompt = Template(
    "\n".join([
        "\n",
        "### Answer the question based on the above context.",
        "### Question:",
        "$query",
        "### Answer:"
    ]))
