# data 目录

运行期产生的文件都在这里，**不会提交到 Git**：

| 目录 | 用途 |
| --- | --- |
| `videos/` | 用户上传的视频文件 |
| `covers/` | 视频封面、轮播图 |
| `avatars/` | 用户头像 |
| `backups/` | `pg_dump` 导出的数据库备份 |

备份与恢复：

```bash
# 后台「备份与维护」里点一下就能备份，等价于：
pg_dump --no-owner --no-privileges -f data/backups/photonv-manual.sql "$DATABASE_URL"

# 恢复
psql "$DATABASE_URL" -f data/backups/photonv-manual.sql
```
