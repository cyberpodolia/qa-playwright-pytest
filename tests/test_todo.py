from __future__ import annotations

from playwright.sync_api import Page, expect

from config import get_settings
from pages.todo_page import TodoPage


def test_add_todo(page: Page):
    settings = get_settings()
    todo = TodoPage(page, settings.base_url)
    todo.open()
    todo.add_todo("write tests")
    expect(page.locator(".todo-list li")).to_have_count(1)


def test_mark_complete(page: Page):
    settings = get_settings()
    todo = TodoPage(page, settings.base_url)
    todo.open()
    todo.add_todo("ship it")
    todo.toggle(0)
    items = todo.get_items()
    assert items[0].completed is True


def test_filter_active_completed(page: Page):
    settings = get_settings()
    todo = TodoPage(page, settings.base_url)
    todo.open()
    todo.add_todo("first")
    todo.add_todo("second")
    todo.toggle(0)

    todo.filter_active()
    expect(page.locator(".todo-list li")).to_have_count(1)

    todo.filter_completed()
    expect(page.locator(".todo-list li")).to_have_count(1)


def test_delete_todo(page: Page):
    settings = get_settings()
    todo = TodoPage(page, settings.base_url)
    todo.open()
    todo.add_todo("remove me")
    todo.delete(0)
    expect(page.locator(".todo-list li")).to_have_count(0)


def test_persistence_in_same_session(page: Page):
    settings = get_settings()
    todo = TodoPage(page, settings.base_url)
    todo.open()
    todo.add_todo("keep me")
    page.reload()
    expect(page.locator(".todo-list li")).to_have_count(1)
