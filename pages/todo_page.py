"""TodoMVC page object used by tests.

Selectors and wait/assert behavior live here so tests read as intent-focused
scenarios instead of low-level Playwright interaction sequences.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from playwright.sync_api import Locator, Page, expect

from pages.base_page import BasePage


@dataclass(frozen=True)
class TodoItem:
    """Simple snapshot of a rendered todo item."""

    text: str
    completed: bool


class TodoPage(BasePage):
    """Page object for TodoMVC actions, filters, and assertions."""

    NEW_TODO = ".new-todo"
    TODO_ITEMS = ".todo-list li"
    TODO_LABEL = "label"
    TODO_TOGGLE = ".toggle"
    TODO_DESTROY = ".destroy"
    TODO_EDIT = ".edit"
    TOGGLE_ALL = ".toggle-all"
    CLEAR_COMPLETED = ".clear-completed"
    FILTERS = ".filters a"
    FOOTER = ".footer"

    def __init__(self, page: Page, base_url: str, timeout_ms: int = 10_000) -> None:
        super().__init__(page=page, base_url=base_url, timeout_ms=timeout_ms)
        self.new_todo_input = page.locator(self.NEW_TODO)
        self.todo_items = page.locator(self.TODO_ITEMS)
        self.filters = page.locator(self.FILTERS)
        self.toggle_all_checkbox = page.locator(self.TOGGLE_ALL)
        self.clear_completed_button = page.locator(self.CLEAR_COMPLETED)

    def open(self) -> None:
        """Open the app and wait for the new-todo input to be ready."""
        self.goto()
        self.expect_visible(self.new_todo_input)

    def item(self, index: int) -> Locator:
        return self.todo_items.nth(index)

    def add_todo(self, text: str) -> str | None:
        """Add one todo and return normalized text, or None when input is empty/whitespace."""
        before = self.todo_items.count()
        self.new_todo_input.fill(text)
        self.new_todo_input.press("Enter")
        created_text = text.strip()
        if not created_text:
            # TodoMVC ignores empty submissions; keep an explicit assertion here for stability.
            expect(self.todo_items).to_have_count(before)
            return None
        expect(self.todo_items).to_have_count(before + 1)
        expect(self.item(before).locator(self.TODO_LABEL)).to_have_text(created_text)
        return created_text

    def add_todos(self, *items: str) -> list[str]:
        created: list[str] = []
        for item in items:
            maybe_text = self.add_todo(item)
            if maybe_text is not None:
                created.append(maybe_text)
        return created

    def toggle(self, index: int, completed: bool | None = None) -> None:
        checkbox = self.item(index).locator(self.TODO_TOGGLE)
        if completed is None:
            checkbox.click()
        elif completed:
            checkbox.check()
        else:
            checkbox.uncheck()

    def toggle_all(self) -> None:
        self.toggle_all_checkbox.check()

    def clear_completed(self) -> None:
        expect(self.clear_completed_button).to_be_visible()
        self.clear_completed_button.click()

    def delete(self, index: int) -> None:
        item = self.item(index)
        before = self.todo_items.count()
        item.hover()
        item.locator(self.TODO_DESTROY).click()
        expect(self.todo_items).to_have_count(before - 1)

    def edit(self, index: int, new_text: str) -> str:
        """Edit an existing item via TodoMVC's double-click inline editor."""
        item = self.item(index)
        item.locator(self.TODO_LABEL).dblclick()
        editor = item.locator(self.TODO_EDIT)
        expect(editor).to_be_visible()
        editor.fill(new_text)
        editor.press("Enter")
        trimmed = new_text.strip()
        expect(item.locator(self.TODO_LABEL)).to_have_text(trimmed)
        return trimmed

    def filter_all(self) -> None:
        self.filters.filter(has_text="All").click()

    def filter_active(self) -> None:
        self.filters.filter(has_text="Active").click()

    def filter_completed(self) -> None:
        self.filters.filter(has_text="Completed").click()

    def assert_count(self, count: int) -> None:
        expect(self.todo_items).to_have_count(count)

    def assert_item_text(self, index: int, text: str) -> None:
        expect(self.item(index).locator(self.TODO_LABEL)).to_have_text(text)

    def assert_item_completed(self, index: int, completed: bool) -> None:
        checkbox = self.item(index).locator(self.TODO_TOGGLE)
        if completed:
            expect(checkbox).to_be_checked()
        else:
            expect(checkbox).not_to_be_checked()

    def assert_filter_hash(self, hash_fragment: str) -> None:
        """Assert URL hash state to verify filter routing, not only visible rows."""
        expect(self.page).to_have_url(re.compile(re.escape(hash_fragment) + r"$"))

    def get_items(self) -> list[TodoItem]:
        """Return a snapshot of visible rows for occasional state-level assertions."""
        items: list[TodoItem] = []
        count = self.todo_items.count()
        for index in range(count):
            row = self.item(index)
            text = row.locator(self.TODO_LABEL).inner_text()
            completed = row.locator(self.TODO_TOGGLE).is_checked()
            items.append(TodoItem(text=text, completed=completed))
        return items

    def get_count(self) -> int:
        return self.todo_items.count()
