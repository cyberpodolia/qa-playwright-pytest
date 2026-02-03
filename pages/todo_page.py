from __future__ import annotations

from dataclasses import dataclass
from typing import List

from playwright.sync_api import Page, expect


@dataclass
class TodoItem:
    text: str
    completed: bool


class TodoPage:
    def __init__(self, page: Page, base_url: str) -> None:
        self.page = page
        self.base_url = base_url
        self.input = page.locator(".new-todo")
        self.list_items = page.locator(".todo-list li")
        self.filters = page.locator(".filters a")

    def open(self) -> None:
        self.page.goto(self.base_url, wait_until="domcontentloaded")
        expect(self.input).to_be_visible()

    def add_todo(self, text: str) -> None:
        count_before = self.list_items.count()
        self.input.fill(text)
        self.input.press("Enter")
        expect(self.list_items).to_have_count(count_before + 1)

    def toggle(self, index: int) -> None:
        item = self.list_items.nth(index)
        item.locator(".toggle").check()

    def delete(self, index: int) -> None:
        item = self.list_items.nth(index)
        item.hover()
        item.locator(".destroy").click()

    def filter_active(self) -> None:
        self.filters.filter(has_text="Active").click()

    def filter_completed(self) -> None:
        self.filters.filter(has_text="Completed").click()

    def get_items(self) -> List[TodoItem]:
        items = []
        count = self.list_items.count()
        for i in range(count):
            item = self.list_items.nth(i)
            text = item.locator("label").inner_text()
            completed = "completed" in (item.get_attribute("class") or "")
            items.append(TodoItem(text=text, completed=completed))
        return items

    def get_count(self) -> int:
        return self.list_items.count()
