from __future__ import annotations

from playwright.sync_api import expect

from pages.todo_page import TodoPage


def test_add_todo(todo_page: TodoPage):
    todo = todo_page
    todo.add_todo("write tests")
    expect(todo.list_items).to_have_count(1)
    items = todo.get_items()
    assert items[0].text == "write tests"
    assert items[0].completed is False


def test_mark_complete(todo_page: TodoPage):
    todo = todo_page
    todo.add_todo("ship it")
    todo.toggle(0)
    items = todo.get_items()
    assert items[0].completed is True


def test_filter_active_completed(todo_page: TodoPage):
    todo = todo_page
    todo.add_todo("first")
    todo.add_todo("second")
    todo.toggle(0)

    todo.filter_active()
    expect(todo.list_items).to_have_count(1)
    assert [item.text for item in todo.get_items()] == ["second"]

    todo.filter_completed()
    expect(todo.list_items).to_have_count(1)
    assert [item.text for item in todo.get_items()] == ["first"]


def test_delete_todo(todo_page: TodoPage):
    todo = todo_page
    todo.add_todo("remove me")
    todo.delete(0)
    expect(todo.list_items).to_have_count(0)


def test_persistence_in_same_session(todo_page: TodoPage):
    todo = todo_page
    todo.add_todo("keep me")
    todo.page.reload()
    todo.wait_for_loaded()
    expect(todo.list_items).to_have_count(1)
