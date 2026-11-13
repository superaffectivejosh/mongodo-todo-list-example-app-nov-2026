"""Add a few friendly examples, once. Existing tasks are never changed or deleted."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import app, lifespan
from app.models import Task

EXAMPLES = [
    ('Make yourself at home', 'This is your space for small steps and big ideas. Edit this task to make it yours.', 'done', 'low'),
    ('Bring your next idea to life', 'Start small. What is one thing you can move forward today?', 'doing', 'high'),
    ('Plan a calmer week', 'Pick three things that matter. Leave a little room for the unexpected.', 'todo', 'medium'),
    ('Try a little fine-tuning', 'Click the pencil to edit a title, add context, or change a priority. Your changes save to MongoDB.', 'todo', 'low'),
    ('Celebrate a small win', 'Finish something, however small. Then click Mark done. Progress deserves a moment.', 'doing', 'medium'),
    ('Make space for what’s next', 'Use the × on a task to delete it. You’ll always get a chance to confirm first.', 'todo', 'low'),
]


async def main():
    async with lifespan(app):
        created = 0
        for title, notes, status, priority in EXAMPLES:
            if await Task.find_one(Task.title == title) is None:
                await Task(title=title, notes=notes, status=status, priority=priority).insert()
                created += 1
        print(f'Added {created} example tasks to {app.state.database_name}.tasks.')


if __name__ == '__main__':
    asyncio.run(main())
