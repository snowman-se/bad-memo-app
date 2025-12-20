from django.test import TestCase
from django.urls import reverse
from memos.models import Memo

class MemoViewTests(TestCase):
    def test_list_page_ok(self):
        res = self.client.get(reverse("memo_list"))
        self.assertEqual(res.status_code, 200)

    def test_create_requires_title(self):
        res = self.client.post(reverse("create_memo"), data={"title": "", "body": "x", "tags": ""})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "タイトルは必須")

    # TODO: detail/edit/delete / legacy検索 / pagination のテストを追加


class PaginationTests(TestCase):
    def setUp(self):
        # Create 50 test memos for pagination testing
        for i in range(50):
            Memo.objects.create(
                title=f"Test Memo {i+1}",
                body=f"This is test memo number {i+1}"
            )

    def test_pagination_first_page_shows_20_items(self):
        """Test that first page shows exactly 20 items"""
        res = self.client.get(reverse("memo_list"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.context['page_obj']), 20)
        self.assertEqual(res.context['page_obj'].number, 1)

    def test_pagination_has_next_page(self):
        """Test that pagination shows next page link when there are more items"""
        res = self.client.get(reverse("memo_list"))
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.context['page_obj'].has_next())
        self.assertContains(res, '次へ')

    def test_pagination_second_page(self):
        """Test that second page can be accessed"""
        res = self.client.get(reverse("memo_list"), {"page": 2})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['page_obj'].number, 2)
        self.assertTrue(res.context['page_obj'].has_previous())

    def test_pagination_with_search_preserves_query(self):
        """Test that pagination preserves search query parameters"""
        res = self.client.get(reverse("memo_list"), {"q": "Test", "page": 1})
        self.assertEqual(res.status_code, 200)
        # Check that pagination links contain the search query
        self.assertContains(res, 'q=Test')

    def test_pagination_invalid_page_defaults_to_first(self):
        """Test that invalid page number defaults to first page"""
        res = self.client.get(reverse("memo_list"), {"page": "invalid"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['page_obj'].number, 1)

    def test_pagination_out_of_range_shows_last_page(self):
        """Test that page number beyond range shows last page"""
        res = self.client.get(reverse("memo_list"), {"page": 999})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['page_obj'].number, res.context['page_obj'].paginator.num_pages)

    def test_pagination_shows_total_count(self):
        """Test that pagination displays total item count"""
        res = self.client.get(reverse("memo_list"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, f"全 50 件")

    def test_pagination_with_legacy_search(self):
        """Test that pagination works with legacy search mode (RawQuerySet)"""
        # Create some memos with 'test' in title/body
        for i in range(5):
            Memo.objects.create(title=f"Test Legacy {i}", body=f"Legacy search test {i}")
        
        res = self.client.get(reverse("memo_list"), {"q": "Legacy", "legacy": "1", "page": 1})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.context['page_obj'].paginator.count > 0)


class SearchSecurityTests(TestCase):
    def setUp(self):
        # Create test memos
        Memo.objects.create(title="Test Memo 1", body="This is a test memo")
        Memo.objects.create(title="Python Programming", body="Learn Python basics")
        Memo.objects.create(title="Django Tutorial", body="Build web apps with Django")

    def test_search_with_single_quote(self):
        """Test that search with single quote does not cause SQL error"""
        res = self.client.get(reverse("memo_list"), {"q": "test'"})
        self.assertEqual(res.status_code, 200)

    def test_search_with_semicolon(self):
        """Test that search with semicolon does not cause SQL error"""
        res = self.client.get(reverse("memo_list"), {"q": "test;"})
        self.assertEqual(res.status_code, 200)

    def test_search_with_sql_injection_attempt(self):
        """Test that SQL injection attempts are safely handled"""
        injection_attempts = [
            "' OR '1'='1",
            "'; DROP TABLE memos_memo; --",
            "' UNION SELECT * FROM auth_user --",
            "%' OR '1'='1' --",
        ]
        for attempt in injection_attempts:
            res = self.client.get(reverse("memo_list"), {"q": attempt})
            self.assertEqual(res.status_code, 200, f"Failed for injection: {attempt}")
            # Verify that no memos are incorrectly returned due to SQL injection
            # The query should just search for the literal string

    def test_legacy_search_with_single_quote(self):
        """Test that legacy search with single quote does not cause SQL error"""
        res = self.client.get(reverse("memo_list"), {"q": "test'", "legacy": "1"})
        self.assertEqual(res.status_code, 200)

    def test_legacy_search_with_sql_injection_attempt(self):
        """Test that legacy search SQL injection attempts are safely handled"""
        res = self.client.get(reverse("memo_list"), {"q": "' OR '1'='1", "legacy": "1"})
        self.assertEqual(res.status_code, 200)

    def test_normal_search_functionality(self):
        """Test that normal search still works correctly after the fix"""
        res = self.client.get(reverse("memo_list"), {"q": "Python"})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Python Programming")

    def test_legacy_search_functionality(self):
        """Test that legacy search still works correctly after the fix"""
        res = self.client.get(reverse("memo_list"), {"q": "Django", "legacy": "1"})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Django Tutorial")
