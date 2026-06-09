import streamlit as st
import sqlite3
import pandas as pd
import os
import qrcode
from PIL import Image
import io
import subprocess
import sys

# 强制安装依赖库
subprocess.check_call([sys.executable, "-m", "pip", "install",
                      "streamlit", "pandas", "qrcode[pil]"])
# 数据库文件路径（自动生成在app.py同目录）
db_path = os.path.join(os.path.dirname(__file__), "platform.db")

# --------------------------
# 扫码溯源页面（必须放最前面）
# --------------------------
animal_id = st.query_params.get("animal_id", None)
if animal_id:
    st.title("🔍 动物溯源信息")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # 查询动物基本信息
    c.execute("SELECT * FROM animals WHERE id = ?", (animal_id,))
    animal = c.fetchone()

    if animal:
        st.subheader(f"动物编号：{animal[0]}")
        st.write(f"**名称：** {animal[1]}")
        st.write(f"**品种：** {animal[2]}")
        st.write(f"**出生日期：** {animal[3]}")
        st.divider()

        # 查询检测记录
        st.subheader("📋 检测记录")
        c.execute("SELECT test_date, pathogen, result FROM detections WHERE animal_id = ? ORDER BY test_date DESC", (animal_id,))
        detections = c.fetchall()

        if detections:
            df = pd.DataFrame(detections, columns=["检测日期", "检测项目", "检测结果"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("暂无检测记录")
    else:
        st.error("❌ 未找到该动物信息")

    conn.close()
    st.stop()

# --------------------------
# 初始化数据库
# --------------------------
def init_db():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS animals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            breed TEXT,
            birth_date TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            animal_id INTEGER,
            test_date TEXT,
            pathogen TEXT,
            result TEXT
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# --------------------------
# 后台主界面（4个标签页）
# --------------------------
st.title("合创快检数据平台")
st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["🐄 动物录入", "🧪 检测录入", "📱 二维码生成", "📊 疫情预测"])

# 标签1：动物信息录入
with tab1:
    st.subheader("动物信息录入")
    with st.form("animal_form", clear_on_submit=True):
        name = st.text_input("动物名称", placeholder="例如：奶牛001")
        breed = st.text_input("品种", placeholder="例如：荷斯坦奶牛")
        birth_date = st.date_input("出生日期")
        submit = st.form_submit_button("提交")

        if submit:
            if not name or not breed:
                st.error("❌ 名称和品种不能为空")
            else:
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                c.execute("INSERT INTO animals (name, breed, birth_date) VALUES (?, ?, ?)",
                          (name, breed, str(birth_date)))
                conn.commit()
                new_id = c.lastrowid
                conn.close()
                st.success(f"✅ 录入成功！ID：{new_id}")

    # 显示所有动物
    st.divider()
    st.subheader("已录入动物")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT * FROM animals")
    animals = c.fetchall()
    conn.close()

    if animals:
        df = pd.DataFrame(animals, columns=["ID", "名称", "品种", "出生日期"])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("暂无动物数据")

# 标签2：检测记录录入
with tab2:
    st.subheader("检测记录录入")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT id, name FROM animals")
    animals = c.fetchall()
    conn.close()

    if animals:
        animal_options = {f"{a[1]} (ID: {a[0]})": a[0] for a in animals}

        with st.form("detection_form", clear_on_submit=True):
            selected_animal = st.selectbox("选择动物", list(animal_options.keys()))
            animal_id = animal_options[selected_animal]

            test_date = st.date_input("检测日期")
            pathogen = st.text_input("检测项目", placeholder="例如：布鲁氏菌")
            result = st.selectbox("检测结果", ["阴性", "阳性"])

            submit_detection = st.form_submit_button("提交")

            if submit_detection:
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                c.execute("INSERT INTO detections (animal_id, test_date, pathogen, result) VALUES (?, ?, ?, ?)",
                          (animal_id, str(test_date), pathogen, result))
                conn.commit()
                conn.close()
                st.success("✅ 检测记录录入成功")
    else:
        st.info("⚠️ 请先录入动物信息")

# 标签3：二维码生成
with tab3:
    st.subheader("生成溯源二维码")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT id, name FROM animals")
    animals = c.fetchall()
    conn.close()

    if animals:
        animal_options = {f"{a[1]} (ID: {a[0]})": a[0] for a in animals}
        selected_qr_animal = st.selectbox("选择动物", list(animal_options.keys()))
        qr_animal_id = animal_options[selected_qr_animal]

        if st.button("生成二维码"):
            # ⚠️ 本地测试：替换为你电脑的局域网IP
            # 部署后：替换为你的Streamlit公网链接
            trace_url = f"http://192.168.3.105:8501/?animal_id={qr_animal_id}"

            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(trace_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)

            st.image(buf, caption=f"{selected_qr_animal} 溯源二维码", width=300)
            st.download_button(
                label="下载二维码",
                data=buf,
                file_name=f"animal_{qr_animal_id}_qrcode.png",
                mime="image/png"
            )
    else:
        st.info("⚠️ 请先录入动物信息")

# 标签4：疫情预测
with tab4:
    st.subheader("疫情趋势预测")
    if st.button("生成未来7天预测"):
        import datetime
        import random

        # 生成未来7天日期
        dates = [str(datetime.date.today() + datetime.timedelta(days=i)) for i in range(7)]
        # 模拟预测数据
        predicted_cases = [random.randint(0, 5) for _ in range(7)]

        prediction_df = pd.DataFrame({
            "日期": dates,
            "预测阳性病例数": predicted_cases
        })

        st.subheader("预测数据")
        st.dataframe(prediction_df, use_container_width=True)

        st.subheader("趋势图")
        st.line_chart(prediction_df, x="日期", y="预测阳性病例数")
