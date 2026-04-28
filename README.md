# AI 穿搭博主 Agent

小红书 AI 虚拟穿搭博主，自动生成穿搭图文内容。

## 快速启动

1. 复制环境配置：
   ```bash
   cp .env.example .env
   # 编辑 .env 填入你的 OPENAI_API_KEY
   ```

2. 安装依赖：
   ```bash
   pip install -e ".[dev]"
   ```

3. 初始化数据：
   ```bash
   python scripts/seed.py
   ```

4. 启动服务：
   ```bash
   uvicorn app.main:app --reload
   ```

5. 访问管理后台: http://localhost:8000

## Docker 启动

```bash
docker compose up -d
```

## API 文档

启动后访问 http://localhost:8000/docs (Swagger UI)

## 项目结构

```
xiaohongshu-agent/
├── app/
│   ├── skills/        # 6个Skill模块
│   ├── routes/        # API路由
│   ├── templates/     # 管理后台页面
│   ├── pipeline.py    # 流程编排
│   └── main.py        # 入口
├── tests/
├── data/              # 商品库+博主人设
├── storage/images/    # 生成的图片
└── docker-compose.yml
```

## 运行测试

```bash
pytest -v
```
