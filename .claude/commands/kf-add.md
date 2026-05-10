Add a new learning subject to KnowledgeFeeder interactively.

Ask the user the following questions (you can ask them all at once):
- What subject do they want to learn?
- What is their current level? (beginner / intermediate / advanced)
- What format do they prefer? (tutorial / flashcards / qa / summary / mixed)
- How often do they want to receive content? (daily / every_2_days / every_3_days / weekly / biweekly)
- What specific topics or areas should be prioritized? (can be a list)
- Any extra instructions for the AI? (e.g. "always include code examples", "focus on practical usage")

Then:
1. Run `./kf.sh add "<subject name>"` to scaffold the folder.
2. Edit the generated `plan.md` to fill in all fields based on the user's answers. Remove the placeholder comments.
3. Show the user the completed `plan.md` and ask if they want any changes.
4. Once confirmed, tell the user they can run `./kf.sh run` to generate the first session, or it will be included in the next scheduled run.
