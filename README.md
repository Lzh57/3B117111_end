# 客戶管理系統

1142 Web 程式設計期末考作業，使用 Flask-WTF + SQLite 實作具備登入驗證的客戶管理系統。

## 使用技術
- Flask + Flask-WTF（表單驗證、CSRF 防護、Session 控制）
- SQLite3（原生模組，未使用 ORM）
- Pico CSS v2（前端樣式）

## 功能
- 登入 / 登出（Session 控管）
- 客戶列表查詢
- 新增客戶（含表單驗證、唯一性檢查）
- 編輯客戶
- 刪除客戶（POST-only + CSRF 防護）

## 安裝與執行

```bash
pip install -r requirements.txt
flask --app app --debug run
```

開啟瀏覽器至 `http://127.0.0.1:5000`

## 預設帳號
| 帳號 | 密碼 |
|------|------|
| admin | admin123 |
