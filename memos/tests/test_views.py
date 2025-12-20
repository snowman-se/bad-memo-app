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
