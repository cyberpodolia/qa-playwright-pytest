from __future__ import annotations

import pytest
from playwright.sync_api import expect

from pages.todo_page import TodoPage


@pytest.mark.smoke
def test_add_todo(todo_page: TodoPage) -> None:
    created = todo_page.add_todo("write tests")
    assert created == "write tests"
    todo_page.assert_count(1)
    todo_page.assert_item_text(0, "write tests")


@pytest.mark.smoke
def test_mark_complete(todo_page: TodoPage) -> None:
    todo_page.add_todo("ship it")
    todo_page.toggle(0, completed=True)
    todo_page.assert_item_completed(0, True)


@pytest.mark.regression
def test_filter_active_completed(todo_page: TodoPage) -> None:
    todo_page.add_todos("first", "second")
    todo_page.toggle(0, completed=True)

    todo_page.filter_active()
    todo_page.assert_count(1)
    todo_page.assert_item_text(0, "second")

    todo_page.filter_completed()
    todo_page.assert_count(1)
    todo_page.assert_item_text(0, "first")


@pytest.mark.regression
def test_delete_todo(todo_page: TodoPage) -> None:
    todo_page.add_todo("remove me")
    todo_page.delete(0)
    todo_page.assert_count(0)


@pytest.mark.regression
def test_persistence_in_same_session(todo_page: TodoPage) -> None:
    # This intentionally checks client-side storage persistence within one browser context.
    todo_page.add_todo("keep me")
    todo_page.page.reload(wait_until="domcontentloaded")
    todo_page.assert_count(1)
    todo_page.assert_item_text(0, "keep me")


@pytest.mark.regression
def test_edit_existing_todo(todo_page: TodoPage) -> None:
    todo_page.add_todo("draft")
    updated = todo_page.edit(0, "finalized")
    assert updated == "finalized"
    todo_page.assert_item_text(0, "finalized")
    todo_page.assert_item_completed(0, False)


@pytest.mark.regression
def test_clear_completed(todo_page: TodoPage) -> None:
    todo_page.add_todos("a", "b", "c")
    todo_page.toggle(0, completed=True)
    todo_page.toggle(2, completed=True)
    todo_page.clear_completed()
    todo_page.assert_count(1)
    todo_page.assert_item_text(0, "b")


@pytest.mark.regression
def test_toggle_all_marks_all_items_completed(todo_page: TodoPage) -> None:
    todo_page.add_todos("one", "two", "three")
    todo_page.toggle_all()
    for index in range(3):
        todo_page.assert_item_completed(index, True)


@pytest.mark.regression
def test_empty_string_is_not_added(todo_page: TodoPage) -> None:
    created = todo_page.add_todo("   ")
    assert created is None
    todo_page.assert_count(0)


@pytest.mark.regression
def test_url_filter_state_updates_hash(todo_page: TodoPage) -> None:
    # Verifies routing state, not just filtered DOM rows.
    todo_page.add_todos("active item", "done item")
    todo_page.toggle(1, completed=True)

    todo_page.filter_active()
    todo_page.assert_filter_hash("#/active")
    todo_page.assert_count(1)
    todo_page.assert_item_text(0, "active item")

    todo_page.filter_completed()
    todo_page.assert_filter_hash("#/completed")
    todo_page.assert_count(1)
    todo_page.assert_item_text(0, "done item")

    todo_page.filter_all()
    todo_page.assert_filter_hash("#/")
    todo_page.assert_count(2)


@pytest.mark.regression
def test_active_filter_hides_completed_items(todo_page: TodoPage) -> None:
    todo_page.add_todos("todo 1", "todo 2")
    todo_page.toggle(0, completed=True)
    todo_page.filter_active()
    expect(todo_page.todo_items).to_have_count(1)
    todo_page.assert_item_text(0, "todo 2")
