# Hu?ng d?n Upstream d? án g?c KrillinAI

Tài li?u này hu?ng d?n cách d?ng b? các thay d?i t? kho luu tr? (repository) g?c c?a KrillinAI sang kho luu tr? fork c?a b?n.

## 1. C?u hình Upstream Remote

N?u chua c?u hình `upstream`, b?n có th? thêm remote tr? v? d? án g?c b?ng l?nh sau:

```bash
git remote add upstream https://github.com/krillinai/KrillinAI.git
```

Ki?m tra l?i danh sách các remote b?ng l?nh:

```bash
git remote -v
```

## 2. Ð?ng b? (Upstream) và gi?i quy?t xung d?t

Ð? l?y các thay d?i m?i nh?t t? nhánh `master` c?a d? án g?c và g?p vào nhánh phát tri?n c?a b?n, s? d?ng các bu?c du?i dây:

### Bu?c 2.1: T?i các nhánh m?i nh?t t? upstream
```bash
git fetch upstream
```

### Bu?c 2.2: Merge thay d?i t? d? án g?c
Khi th?c hi?n g?p (merge), n?u x?y ra xung d?t (conflict), chúng ta mu?n uu tiên gi? l?i các thay d?i c?a kho luu tr? fork hi?n t?i. S? d?ng c? `-X ours` d? t? d?ng ch?n code c?a ta khi có conflict:

```bash
git merge upstream/master -X ours -m "merge: merge upstream/master into master, preferring current fork changes on conflict"
```

*Luu ý:* C? `-X ours` gi?i quy?t các conflict ? m?c dòng (hunk-level conflicts) m?t cách t? d?ng b?ng cách ch?n phiên b?n c?a chúng ta. Ð?i v?i các file m?i ho?c nh?ng conflict l?n hon, hãy ki?m tra l?i b?ng `git status`.

### Bu?c 2.3: Ð?y code m?i lên kho luu tr? fork c?a b?n
Sau khi merge thành công, c?p nh?t các thay d?i lên GitHub c?a b?n:

```bash
git push origin master
```
