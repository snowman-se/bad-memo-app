from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from .models import Memo
from .utils import normalize_q, parse_sort, now_jst_string

# NOTE: 教材用。わざと“読みにくい/危ない”実装が入っています。
# - legacy=1 の場合、旧実装として“生SQL文字列を組み立てる”検索が動く（危険/壊れやすい）
# - ページネーション無しで一覧が重い
# 目標: Copilot を使って、危険な実装を見つけて安全な形に直す。


def memo_list(request: HttpRequest) -> HttpResponse:
    q = normalize_q(request.GET.get("q"))
    tag = (request.GET.get("tag") or "").strip().lower()
    sort = request.GET.get("sort") or "new"
    legacy = (request.GET.get("legacy") == "1")
    unsafe_sort = (request.GET.get("unsafe_sort") == "1")
    page_number = request.GET.get("page", 1)

    memos = Memo.objects.all()

    if legacy and q:
        sql = (
            "SELECT * FROM memos_memo "
            "WHERE title LIKE %s "
            "OR body LIKE %s "
            "ORDER BY created_at DESC"
        )
        search_pattern = f"%{q}%"
        memos = Memo.objects.raw(sql, [search_pattern, search_pattern])

    else:
        if q:
            sql = (
                "SELECT * FROM memos_memo "
                "WHERE title LIKE %s "
                "OR body LIKE %s "
                "ORDER BY created_at DESC"
            )
            search_pattern = f"%{q}%"
            memos = Memo.objects.raw(sql, [search_pattern, search_pattern])
        if tag:
            memos = memos.filter(tags__name=tag)

    # Pagination: 20 items per page
    paginator = Paginator(memos, 20)
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    context = {
        "page_obj": page_obj,
        "memos": page_obj,  # Keep memos for backward compatibility with template
        "q": q,
        "tag": tag,
        "sort": sort,
        "legacy": legacy,
        "unsafe_sort": unsafe_sort
    }
    return render(request, "memos/memo_list.html", context)



def memo_detail(request: HttpRequest, memo_id: int) -> HttpResponse:
    memo = Memo.objects.get(id=memo_id)  # 怪しいところ: 404にならない
    return render(request, "memos/memo_detail.html", {"memo": memo})


def create_memo(request: HttpRequest) -> HttpResponse:
    error = None
    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        body = request.POST.get("body") or ""
        tags = request.POST.get("tags") or ""

        if len(title) == 0:
            error = "タイトルは必須です"
        elif len(title) > 120:
            error = "タイトルが長すぎます（120文字まで）"
        else:
            m = Memo(title=title, body=body)
            m.save()
            m.attach_tags_from_csv(tags)
            messages.success(request, f"保存しました ({now_jst_string()})")
            return redirect("memo_detail", memo_id=m.id)

    return render(request, "memos/memo_form.html", {"mode": "新規作成", "memo": {}, "tags": "", "error": error})


def edit_memo(request: HttpRequest, memo_id: int) -> HttpResponse:
    error = None
    memo = Memo.objects.get(id=memo_id)  # 怪しいところ: 404にならない

    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        body = request.POST.get("body") or ""
        tags = request.POST.get("tags") or ""

        if len(title) == 0:
            error = "タイトルは必須です"
        elif len(title) > 120:
            error = "タイトルが長すぎます（120文字まで）"
        else:
            memo.title = title
            memo.body = body
            memo.save()

            memo.tags.clear()  # 怪しいところ: 雑に全消し
            memo.attach_tags_from_csv(tags)

            messages.success(request, f"更新しました ({now_jst_string()})")
            return redirect("memo_detail", memo_id=memo.id)

    tag_csv = ",".join([t.name for t in memo.tags.all()])
    return render(request, "memos/memo_form.html", {"mode": "編集", "memo": memo, "tags": tag_csv, "error": error})


def delete_memo(request: HttpRequest, memo_id: int) -> HttpResponse:
    # 怪しいところ: POST 以外でも削除できる（教材で直す）
    try:
        memo = Memo.objects.get(id=memo_id)
        memo.delete()
        messages.success(request, "削除しました")
    except Exception:
        messages.error(request, "削除に失敗しました")
    return redirect("memo_list")
