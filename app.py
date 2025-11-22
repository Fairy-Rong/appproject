import json
import streamlit as st
import pandas as pd   # ← 新增

# ----------------- 页面全局配置 -----------------

st.set_page_config(
    page_title="记忆分类人工审核器",
    layout="wide",
)

# 可选的类型标签（如有其它类型可自行添加）
TYPE_OPTIONS = ["A", "B", "C", "D"]

# 记忆标签：多了一个 "remove" 表示删除此记忆
LABEL_OPTIONS = ["must", "nice", "irr", "remove"]


# ----------------- 工具函数：session_state & 数据预处理 -----------------

def init_session_state():
    """初始化 session_state 中需要用到的键"""
    if "data" not in st.session_state:
        st.session_state.data = None          # 当前加载的数据集：list[dict]
    if "sample_idx" not in st.session_state:
        st.session_state.sample_idx = 0       # 当前查看的样本 index
    if "uploaded_name" not in st.session_state:
        st.session_state.uploaded_name = None # 上传文件名，用于导出命名


def ensure_flat_memory(sample: dict):
    """
    确保 sample 内有 `_flat_memory` 字段：
    - _flat_memory 是一个 list，每一项结构为：
      {
        "flat_id": int,            # 在本 sample 中的固定编号
        "fact": str,
        "why": str,
        "orig_label": "must/nice/irr",
        "current_label": "must/nice/irr/remove"
      }
    - orig_label 来自原始 memory，不随编辑变化
    - current_label 可以编辑
    """
    if "_flat_memory" in sample:
        return

    flat = []
    flat_id = 0
    memory = sample.get("memory", {})

    # 原始顺序：先 must，再 nice，再 irr，各自维持原来的条目顺序
    for orig_label in ["must", "nice", "irr"]:
        for item in memory.get(orig_label, []):
            flat.append(
                {
                    "flat_id": flat_id,
                    "fact": item.get("fact", ""),
                    "why": item.get("why", ""),
                    "orig_label": orig_label,
                    "current_label": orig_label,  # 初始时当前标签=原标签
                }
            )
            flat_id += 1

    sample["_flat_memory"] = flat


def preprocess_data(data):
    """对整个数据集做一次预处理，给每个 sample 补上 _flat_memory"""
    for sample in data:
        ensure_flat_memory(sample)


def load_json_file(uploaded_file):
    """从上传文件中解析 JSON（顶层必须是 list），并预处理 flat_memory"""
    content = uploaded_file.read().decode("utf-8")
    data = json.loads(content)
    if not isinstance(data, list):
        raise ValueError("JSON 顶层结构必须是一个 list（样本列表）")
    preprocess_data(data)
    return data


def clear_sample_widgets(idx: int):
    """
    清理指定样本的所有 widget key，避免切换样本时的状态冲突：
    - given_type / inferred_type
    - 每条记忆的 fact / why / label
    """
    data = st.session_state.data
    sample = data[idx]
    ensure_flat_memory(sample)

    # 类型选择
    for key in [f"given_type_{idx}", f"inferred_type_{idx}"]:
        if key in st.session_state:
            del st.session_state[key]

    # 记忆相关
    for item in sample["_flat_memory"]:
        fid = item["flat_id"]
        for prefix in ["fact", "why", "label"]:
            key = f"{prefix}_{idx}_{fid}"
            if key in st.session_state:
                del st.session_state[key]


# ----------------- 核心：保存当前样本 -----------------

def save_current_sample(idx: int):
    """
    从界面控件状态，把当前样本的改动写回 st.session_state.data[idx]。
    - 更新 given_type / inferred_type
    - 更新 _flat_memory 中每条记忆的 fact / why / current_label
    - 再根据 current_label 重新组装 memory = {must/nice/irr}
      （remove 的条目会被丢弃）
    """
    data = st.session_state.data
    sample = data[idx]
    ensure_flat_memory(sample)

    # ---- 顶层 type 字段 ----
    old_given = sample.get("given_type")
    old_inferred = sample.get("inferred_type")

    # 如果原值不在 TYPE_OPTIONS 里，就默认用第一个
    given = st.session_state.get(f"given_type_{idx}", old_given)
    if given not in TYPE_OPTIONS:
        given = TYPE_OPTIONS[0]
    inferred = st.session_state.get(f"inferred_type_{idx}", old_inferred)
    if inferred not in TYPE_OPTIONS:
        inferred = TYPE_OPTIONS[0]

    sample["given_type"] = given
    sample["inferred_type"] = inferred

    # ---- 更新 flat_memory 中每条记忆 ----
    flat = sample["_flat_memory"]
    for item in flat:
        fid = item["flat_id"]

        fact_key = f"fact_{idx}_{fid}"
        why_key = f"why_{idx}_{fid}"
        label_key = f"label_{idx}_{fid}"

        # 读取最新的 fact / why
        item["fact"] = st.session_state.get(fact_key, item["fact"])
        item["why"] = st.session_state.get(why_key, item["why"])

        # 读取最新的标签（当前标签）
        cur_label = st.session_state.get(label_key, item.get("current_label", item["orig_label"]))
        if cur_label not in LABEL_OPTIONS:
            cur_label = item.get("current_label", item["orig_label"])
            if cur_label not in LABEL_OPTIONS:
                cur_label = item["orig_label"]  # 再兜一层
        item["current_label"] = cur_label

    # ---- 根据 current_label 重新构建 memory 字段 ----
    new_memory = {"must": [], "nice": [], "irr": []}

    for item in flat:
        label = item["current_label"]
        if label == "remove":
            # 标注师选择删除这条记忆
            continue

        # 安全兜底：如果 label 不在 must/nice/irr 中，则退回 orig_label
        if label not in new_memory:
            label = item["orig_label"] if item["orig_label"] in new_memory else "irr"

        new_memory[label].append(
            {
                "fact": item["fact"],
                "why": item["why"],
            }
        )

    sample["memory"] = new_memory
    data[idx] = sample
    st.session_state.data = data


# ----------------- 显示 & 编辑样本 -----------------

def display_sample(idx: int):
    """主界面：显示并可编辑当前样本（含记忆内容/标签）"""
    data = st.session_state.data
    sample = data[idx]
    ensure_flat_memory(sample)

    st.markdown(f"### 样本 {idx + 1} / {len(data)}  ——  id: `{sample.get('id', '')}`")

    # -------- 基本信息 --------
    st.markdown("#### 基本信息")

    st.write(f"**Query**: {sample.get('query', '')}")
    st.write(f"**Query Time**: {sample.get('query_time', '')}")

    roles = sample.get("roles", {})
    st.write(
        f"**Human**: {roles.get('human', '')}    |    **Virtual Person**: {roles.get('virtual_person', '')}"
    )

    # ---- type 可编辑 ----
    given_type = sample.get("given_type", TYPE_OPTIONS[0])
    inferred_type = sample.get("inferred_type", TYPE_OPTIONS[0])

    col1, col2 = st.columns(2)
    with col1:
        if given_type not in TYPE_OPTIONS:
            given_type = TYPE_OPTIONS[0]
        st.selectbox(
            "given_type",
            TYPE_OPTIONS,
            index=TYPE_OPTIONS.index(given_type),
            key=f"given_type_{idx}",
        )
    with col2:
        if inferred_type not in TYPE_OPTIONS:
            inferred_type = TYPE_OPTIONS[0]
        st.selectbox(
            "inferred_type",
            TYPE_OPTIONS,
            index=TYPE_OPTIONS.index(inferred_type),
            key=f"inferred_type_{idx}",
        )

    # ---- history 展示 ----
    history = sample.get("history", "")
    if history:
        with st.expander("展开查看 history"):
            st.text(history)

    st.markdown("---")

    # -------- 记忆内容编辑（fact / why / 标签） --------
    st.markdown("### 记忆内容编辑")

    flat = sample["_flat_memory"]
    if not flat:
        st.write("_当前样本暂无记忆_")
    else:
        for i, item in enumerate(flat):
            fid = item["flat_id"]
            orig_label = item["orig_label"]

            st.markdown(f"#### 记忆 #{i + 1}")

            fact_key = f"fact_{idx}_{fid}"
            why_key = f"why_{idx}_{fid}"
            label_key = f"label_{idx}_{fid}"

            # fact / why 文本编辑
            st.text_area(
                "fact",
                value=item["fact"],
                key=fact_key,
                height=80,
            )
            st.text_area(
                "why（理由，可以修改）",
                value=item["why"],
                key=why_key,
                height=60,
            )

            # 原标签 & 当前标签
            c1, c2 = st.columns([1, 2])
            with c1:
                st.markdown(f"原标签：`{orig_label.upper()}`")
            with c2:
                # 当前标签从 session_state 或 item.current_label 取值
                current_label = st.session_state.get(
                    label_key,
                    item.get("current_label", orig_label),
                )
                if current_label not in LABEL_OPTIONS:
                    current_label = item.get("current_label", orig_label)
                    if current_label not in LABEL_OPTIONS:
                        current_label = orig_label

                st.selectbox(
                    "当前标签（可修改）",
                    LABEL_OPTIONS,
                    index=LABEL_OPTIONS.index(current_label),
                    key=label_key,
                )

            st.markdown("---")

    st.info("提示：上面可以同时修改 fact / why / 当前标签。切换样本或导出前会自动保存当前样本。")
    # -------- 所有记忆总览（flat list）--------
    st.markdown("---")
    st.markdown("### 当前样本所有记忆总览（原标签 & 当前标签）")

    rows = []
    for item in flat:
        fid = item["flat_id"]
        orig_label = item["orig_label"]

        fact_key = f"fact_{idx}_{fid}"
        why_key = f"why_{idx}_{fid}"
        label_key = f"label_{idx}_{fid}"

        # ---- 获取最新 fact/why（若未改动则使用 item 内的值）----
        cur_fact = st.session_state.get(fact_key, item.get("fact", ""))
        cur_why = st.session_state.get(why_key, item.get("why", ""))

        # ---- 当前标签（若未改动则使用 item.current_label 或 orig_label）----
        cur_label = st.session_state.get(
            label_key,
            item.get("current_label", orig_label)
        )
        if cur_label not in LABEL_OPTIONS:
            cur_label = item.get("current_label", orig_label)
        if cur_label == "remove":
            continue  # 不展示被 remove 的记录

        rows.append(
            {
                "原标签": orig_label,
                "当前标签": cur_label,
                "fact": cur_fact,
                "why": cur_why,
            }
        )

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)
    else:
        st.write("_当前样本暂无可展示的记忆_")


# ----------------- 主程序入口 -----------------

def main():
    init_session_state()

    st.title("✨ 记忆分类人工审核器（Streamlit）")

    st.markdown(
        """
本工具用于人工审核虚拟人记忆数据集中 `must / nice / irr` 的分类是否合理。

**使用方式（每位数据标注师）：**
1. 在左侧上传自己那一份 JSON 数据集（顶层必须是 list，每个元素是一个样本 dict）。
2. 在中间界面逐条查看样本，编辑：
   - `given_type` / `inferred_type`
   - 每条记忆的 `fact` / `why`
   - 每条记忆的“当前标签”（must / nice / irr / remove）
   - “原标签”是导入时的标签，仅作参考，不会被修改。
3. 完成后点击下方“下载标注后的 JSON 文件”，将结果保存本地并交回。

> 说明：
> - 同一台服务器上，多位标注师可以同时使用这个页面；每个人的浏览器会话互相独立。
> - 只要不关闭标签页 / 不强制刷新（Ctrl+R / F5），进度会一直保存在当前浏览器会话的内存里。
> - 服务器重启或你关闭浏览器后，需要重新上传 JSON；建议工作一段时间就下载一次备份。
"""
    )

    st.sidebar.header("📂 数据加载")

    # 已经有数据的情况：显示文件名 & 清空按钮
    if st.session_state.data is not None and st.session_state.uploaded_name:
        st.sidebar.success(
            f"✅ 已加载文件：{st.session_state.uploaded_name}\n"
            f"共 {len(st.session_state.data)} 条样本"
        )
        if st.sidebar.button("🔄 清空并重新上传", use_container_width=True):
            st.session_state.data = None
            st.session_state.uploaded_name = None
            st.session_state.sample_idx = 0
            st.rerun()
    else:
        # 只有在没有数据时才显示文件上传器
        uploaded_file = st.sidebar.file_uploader(
            "上传 JSON 文件（UTF-8 编码）", type=["json"], key="file_uploader"
        )

        if uploaded_file is not None:
            try:
                data = load_json_file(uploaded_file)
                st.session_state.data = data
                st.session_state.sample_idx = 0
                st.session_state.uploaded_name = uploaded_file.name
                st.sidebar.success(
                    f"已加载文件：{uploaded_file.name}，共 {len(data)} 条样本。"
                )
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"解析 JSON 失败：{e}")

    # 若还没有数据，直接提示并返回
    if st.session_state.data is None:
        st.warning("请先在左侧上传一个 JSON 数据集文件。")
        return

    data = st.session_state.data
    n_samples = len(data)

    st.markdown("---")
    st.subheader("📑 样本浏览与编辑")

    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])

    # 上一条
    with col_nav1:
        if st.button("⬅️ 上一条", use_container_width=True):
            save_current_sample(st.session_state.sample_idx)
            old_idx = st.session_state.sample_idx
            if st.session_state.sample_idx > 0:
                st.session_state.sample_idx -= 1
                clear_sample_widgets(old_idx)
            st.rerun()

    # 下一条
    with col_nav3:
        if st.button("下一条 ➡️", use_container_width=True):
            save_current_sample(st.session_state.sample_idx)
            old_idx = st.session_state.sample_idx
            if st.session_state.sample_idx < n_samples - 1:
                st.session_state.sample_idx += 1
                clear_sample_widgets(old_idx)
            st.rerun()

    # 跳转
    with col_nav2:
        cur = st.session_state.sample_idx + 1
        new_idx_display = st.number_input(
            "跳转到第几条（1-based）",
            min_value=1,
            max_value=n_samples,
            value=cur,
            step=1,
        )
        if new_idx_display != cur:
            save_current_sample(st.session_state.sample_idx)
            old_idx = st.session_state.sample_idx
            st.session_state.sample_idx = new_idx_display - 1
            clear_sample_widgets(old_idx)
            st.rerun()

    st.markdown("---")

    # 显示当前样本
    display_sample(st.session_state.sample_idx)

    # 手动保存按钮（其实在切换样本 & 导出时也会自动保存）
    if st.button("✅ 保存当前样本修改"):
        save_current_sample(st.session_state.sample_idx)
        st.success("当前样本已保存到当前会话的内存中。")

    st.markdown("---")
    st.subheader("📥 导出标注结果")

    # 导出前再保存一次当前样本
    save_current_sample(st.session_state.sample_idx)

    json_str = json.dumps(st.session_state.data, ensure_ascii=False, indent=2)
    download_filename = (
        (st.session_state.uploaded_name or "labeled_data.json").replace(".json", "")
        + "_labeled.json"
    )

    st.download_button(
        "⬇️ 下载标注后的 JSON 文件",
        data=json_str.encode("utf-8"),
        file_name=download_filename,
        mime="application/json",
    )

    st.caption("提示：下载的是当前会话内存中的全部样本，包括你已经修改保存的内容。")


if __name__ == "__main__":
    main()
