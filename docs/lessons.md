# Lessons from daily use

What daily use of the kit taught. These are not vault rules (those live in `CLAUDE.md`); they are habits of whoever runs it.

1. **The script computes, the model writes.** Anything that must come out the same every time (counts, dates, integrity, calculations) goes in a tested script. The model reads the result and explains it.
2. **Write rules once.** If you catch yourself repeating an instruction in the chat, it belongs in `CLAUDE.md`. If you repeat a workflow, it becomes a slash command.
3. **Files, not pasted text.** Put the source in `raw/` and pass the path. What is pasted into the chat is neither recorded nor auditable.
4. **Plan before editing.** Ask for the plan, answer it, and only then let it write. `/ingest` already works that way.
5. **Nothing is done without evidence.** Ask it to run the lint or the tests and show you the output.
6. **Validated text is moved, not rewritten.** Text you already reviewed is copied as is. If the model "improves" it, you have to review it again.
7. **A repeated mistake becomes a rule, and the rule is born with its check** (MAESTRO rule 9).
8. **Close every session.** Before stopping: have it update what changed, record it in the log and leave you a prompt to resume in a new window. The next session starts without relying on memory.
9. **Place each operation on the decision matrix** before automating it (see `decision-rights.md`).
