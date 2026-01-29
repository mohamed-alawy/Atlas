from string import Template

### RAG PROMPT TEMPLATES - ARABIC ###

### SYSTEM TEMPLATES ###
system_prompt = Template(
    "\n".join([
        "أنت مساعد ذكاء اصطناعي يساعد الناس في العثور على المعلومات.",
        "استخدم السياق المقدم للإجابة على السؤال بأقصى قدر من الدقة.",
        "إذا لم يتضمن السياق الإجابة، أجب بـ 'لا أعرف'.",
        "يجب أن تجيب بلغة السؤال.",
        "كن مهذبًا ومهنيًا في ردودك.",
        "كن مختصرًا ومباشرًا."
    ])
)

### DOCUMENT RETRIEVAL TEMPLATES ###
document_prompt = Template(
    "\n".join([
        "## المستند رقم: $doc_index:",
        "## المحتوى: $chunk_text",
    ])
)

### FOOTER TEMPLATES ###
footer_prompt = Template(
    "\n".join([
        "\n",
        "### أجب عن السؤال بناءً على السياق أعلاه.",
        "### السؤال:",
        "$query",
        "### الإجابة:"
    ])
)