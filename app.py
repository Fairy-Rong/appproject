# import json
# import streamlit as st

# # ----------------- 页面全局配置 -----------------

# st.set_page_config(
#     page_title="记忆分类人工审核器",
#     layout="wide",
# )

# # 可选的类型标签
# TYPE_OPTIONS = ["A", "B", "C", "D"]
# # 记忆标签（含 remove）
# LABEL_OPTIONS = ["must", "nice", "irr", "remove"]


# # ----------------- 会话状态初始化 -----------------

# def init_session_state():
#     """初始化 session_state 中需要用到的键"""
#     if "data" not in st.session_state:
#         st.session_state.data = None         # 当前加载的数据集：list[dict]
#     if "sample_idx" not in st.session_state:
#         st.session_state.sample_idx = 0      # 当前查看的样本 index
#     if "uploaded_name" not in st.session_state:
#         st.session_state.uploaded_name = None  # 上传文件名，用于导出命名


# # ----------------- 数据加载与保存 -----------------
# def load_json_file(uploaded_file):
#     """从上传文件中解析 JSON（顶层必须是 list），并为每条记忆打上原标签和唯一 ID"""
#     content = uploaded_file.read().decode("utf-8")
#     data = json.loads(content)
#     if not isinstance(data, list):
#         raise ValueError("JSON 顶层结构必须是一个 list（样本列表）")

#     # 为每条 memory 打上 _orig_group 和 _uid，后续用来展示“原标签”和稳定绑定控件
#     for si, sample in enumerate(data):
#         memory = sample.get("memory", {})
#         for group in ["must", "nice", "irr"]:
#             facts = memory.get(group, [])
#             for ji, item in enumerate(facts):
#                 # 原始标签（只在第一次导入时确定，之后不再变化）
#                 if "_orig_group" not in item:
#                     item["_orig_group"] = group
#                 # 唯一 ID（用来做 streamlit widget key，避免 index 变化导致串联）
#                 if "_uid" not in item:
#                     item["_uid"] = f"s{si}_{group}_{ji}"

#     return data



# def save_current_sample(idx):
#     """
#     把当前样本（idx）的改动写回 st.session_state.data[idx]。
#     这里按每条记忆的 _uid 读写，保证不会出现“改一条，其它跟着变”的问题。
#     """
#     data = st.session_state.data
#     sample = data[idx]

#     # ---- 顶层 type 字段 ----
#     sample["given_type"] = st.session_state.get(
#         f"given_type_{idx}", sample.get("given_type")
#     )
#     sample["inferred_type"] = st.session_state.get(
#         f"inferred_type_{idx}", sample.get("inferred_type")
#     )

#     memory = sample.get("memory", {})

#     # 新的分组容器
#     new_memory = {"must": [], "nice": [], "irr": []}

#     # 遍历当前 sample 中所有记忆条目（按 group 聚合）
#     for group in ["must", "nice", "irr"]:
#         for item in memory.get(group, []):
#             uid = item.get("_uid")
#             if not uid:
#                 # 理论上不会发生；兜底一个
#                 uid = f"tmp_{group}_{id(item)}"
#                 item["_uid"] = uid

#             fact_key = f"fact_{uid}"
#             why_key = f"why_{uid}"
#             label_key = f"label_{uid}"

#             fact_text = st.session_state.get(fact_key, item.get("fact", ""))
#             why_text = st.session_state.get(why_key, item.get("why", ""))

#             # 当前标签：优先用控件中的值，否则用当前分组
#             cur_label = st.session_state.get(label_key, group)

#             # 如果选择了 remove，就直接丢弃这条记忆
#             if cur_label == "remove":
#                 continue

#             if cur_label not in new_memory:
#                 cur_label = group  # 容错兜底

#             # 保留 _orig_group，不随当前标签变化
#             new_item = {
#                 "fact": fact_text,
#                 "why": why_text,
#             }
#             if "_orig_group" in item:
#                 new_item["_orig_group"] = item["_orig_group"]
#             else:
#                 new_item["_orig_group"] = group

#             # 保留唯一 ID，保证下次 rerun 时还是同一条
#             new_item["_uid"] = uid

#             new_memory[cur_label].append(new_item)

#     sample["memory"] = new_memory
#     data[idx] = sample
#     st.session_state.data = data

# def clear_sample_widgets(idx):
#     """清理指定样本的所有 widget key（按 _uid 精确清理）"""
#     data = st.session_state.data
#     sample = data[idx]

#     # type 的 key
#     for key in [f"given_type_{idx}", f"inferred_type_{idx}"]:
#         if key in st.session_state:
#             del st.session_state[key]

#     # memory 相关 key
#     memory = sample.get("memory", {})
#     for group in ["must", "nice", "irr"]:
#         for item in memory.get(group, []):
#             uid = item.get("_uid")
#             if not uid:
#                 continue
#             for prefix in ["fact_", "why_", "label_"]:
#                 k = f"{prefix}{uid}"
#                 if k in st.session_state:
#                     del st.session_state[k]

# def display_sample(idx):
#     """主界面：显示并可编辑当前样本（统一的记忆内容编辑 + 标签修改）"""
#     data = st.session_state.data
#     sample = data[idx]

#     st.markdown(f"### 样本 {idx + 1} / {len(data)}  ——  id: `{sample.get('id', '')}`")

#     st.markdown("#### 基本信息")

#     st.write(f"**Query**: {sample.get('query', '')}")
#     st.write(f"**Query Time**: {sample.get('query_time', '')}")

#     roles = sample.get("roles", {})
#     st.write(
#         f"**Human**: {roles.get('human', '')}    |    **Virtual Person**: {roles.get('virtual_person', '')}"
#     )

#     # ---- type 可编辑 ----
#     given_type = sample.get("given_type", "unknown")
#     inferred_type = sample.get("inferred_type", "unknown")

#     col1, col2 = st.columns(2)
#     with col1:
#         if given_type not in TYPE_OPTIONS:
#             given_idx = 0
#         else:
#             given_idx = TYPE_OPTIONS.index(given_type)

#         st.selectbox(
#             "given_type",
#             TYPE_OPTIONS,
#             index=given_idx,
#             key=f"given_type_{idx}",
#         )
#     with col2:
#         if inferred_type not in TYPE_OPTIONS:
#             inferred_idx = 0
#         else:
#             inferred_idx = TYPE_OPTIONS.index(inferred_type)

#         st.selectbox(
#             "inferred_type",
#             TYPE_OPTIONS,
#             index=inferred_idx,
#             key=f"inferred_type_{idx}",
#         )

#     # ---- history 简单展示 ----
#     history = sample.get("history", "")
#     if history:
#         with st.expander("展开查看 history"):
#             st.text(history)

#     st.markdown("---")
#     st.markdown("### 记忆内容编辑")

#     memory = sample.get("memory", {})

#     # 扁平化所有记忆，统一编辑
#     flat_items = []
#     for group in ["must", "nice", "irr"]:
#         for item in memory.get(group, []):
#             flat_items.append((group, item))

#     if not flat_items:
#         st.write("_当前样本暂无记忆_")
#         return

#     for idx_row, (cur_group, item) in enumerate(flat_items, start=1):
#         uid = item.get("_uid")
#         if not uid:
#             uid = f"tmp_{cur_group}_{id(item)}"
#             item["_uid"] = uid

#         fact_key = f"fact_{uid}"
#         why_key = f"why_{uid}"
#         label_key = f"label_{uid}"

#         orig_group = item.get("_orig_group", cur_group)

#         st.markdown(f"**记忆 #{idx_row}**")

#         col_left, col_right = st.columns([3, 2])

#         with col_left:
#             st.text_area(
#                 "fact",
#                 value=item.get("fact", ""),
#                 key=fact_key,
#                 height=80,
#             )
#             st.text_area(
#                 "why（理由，可以修改）",
#                 value=item.get("why", ""),
#                 key=f"why_{uid}",
#                 height=60,
#             )

#         with col_right:
#             st.write(f"**原标签（导入时）**：`{orig_group}`")
#             # 当前标签：优先用 session_state 中的值，否则用当前所在分组
#             current_label = st.session_state.get(label_key, cur_group)
#             if current_label not in LABEL_OPTIONS:
#                 current_label = cur_group
#             label_idx = LABEL_OPTIONS.index(current_label)

#             st.selectbox(
#                 "当前标签（可修改）",
#                 LABEL_OPTIONS,
#                 index=label_idx,
#                 key=label_key,
#             )

#         st.markdown("---")

#     st.info("提示：上面既可修改 fact / why，也可修改标签（原标签仅展示，不会随编辑变化）。")


# def get_clean_data_for_export():
#     """导出前去掉每条记忆上的内部字段（_uid, _orig_group）"""
#     clean_data = []
#     for sample in st.session_state.data:
#         new_sample = {k: v for k, v in sample.items() if k != "memory"}
#         memory = sample.get("memory", {})
#         new_mem = {}
#         for group in ["must", "nice", "irr"]:
#             new_mem[group] = []
#             for item in memory.get(group, []):
#                 new_item = {
#                     k: v
#                     for k, v in item.items()
#                     if k not in ["_uid", "_orig_group"]
#                 }
#                 new_mem[group].append(new_item)
#         new_sample["memory"] = new_mem
#         clean_data.append(new_sample)
#     return clean_data


# # ----------------- 主程序入口 -----------------

# def main():
#     init_session_state()

#     st.title("✨ 记忆分类人工审核器（Streamlit）")

#     st.markdown(
#         """
# 本工具用于人工审核虚拟人记忆数据集中 `must / nice / irr` 的分类是否合理。

# **使用方式：**
# - 每位数据标注师：
#   1. 在左侧上传自己那一份 JSON 数据集（顶层必须是 list，每个元素是一个样本 dict）。
#   2. 在中间界面编辑 samples：
#      - 修改 `given_type` / `inferred_type`
#      - 在上方的「记忆内容编辑」里修改每条记忆的 `fact` 和 `why`
#      - 在下方「标签总览」中，查看每条记忆的**原标签**，并通过下拉框修改为 `must / nice / irr / remove`
#   3. 完成一段后，点击“下载标注后的 JSON 文件”，把结果文件保存回本地并交回即可。

# > 注意：  
# > - 同一台服务器上，多位标注师可以同时使用这个页面；每个人的浏览器会话互相独立。  
# > - 只要不关闭标签页 / 不强制刷新（Ctrl+R / F5），进度会一直保存在当前浏览器会话的内存里。  
# > - 服务器重启或你关闭浏览器后，需要重新上传 JSON；因此建议工作一段时间就下载一次备份。
# """
#     )

#     st.sidebar.header("📂 数据加载")

#     # 如果已经有数据，显示当前加载的文件名（刷新后仍保留在本次会话中）
#     if st.session_state.data is not None and st.session_state.uploaded_name:
#         st.sidebar.success(
#             f"✅ 已加载文件：{st.session_state.uploaded_name}\n"
#             f"共 {len(st.session_state.data)} 条样本"
#         )
#         if st.sidebar.button("🔄 清空并重新上传", use_container_width=True):
#             # 仅清空当前浏览器会话的状态，不影响其他人
#             st.session_state.data = None
#             st.session_state.uploaded_name = None
#             st.session_state.sample_idx = 0
#             st.rerun()
#     else:
#         # 只有在没有数据时才显示文件上传器
#         uploaded_file = st.sidebar.file_uploader(
#             "上传 JSON 文件（UTF-8 编码）", type=["json"], key="file_uploader"
#         )

#         # 只在真正上传新文件时加载数据
#         if uploaded_file is not None:
#             try:
#                 data = load_json_file(uploaded_file)
#                 st.session_state.data = data
#                 st.session_state.sample_idx = 0
#                 st.session_state.uploaded_name = uploaded_file.name
#                 st.sidebar.success(
#                     f"已加载文件：{uploaded_file.name}，共 {len(data)} 条样本。"
#                 )
#                 st.rerun()  # 重新运行以更新界面
#             except Exception as e:
#                 st.sidebar.error(f"解析 JSON 失败：{e}")

#     # 没有数据时给一点提示
#     if st.session_state.data is None:
#         st.warning("请先在左侧上传一个 JSON 数据集文件。")
#         return

#     data = st.session_state.data
#     n_samples = len(data)

#     # 顶部进度 & 跳转
#     st.markdown("---")
#     st.subheader("📑 样本浏览与编辑")

#     col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])

#     # 上一条
#     with col_nav1:
#         if st.button("⬅️ 上一条", use_container_width=True):
#             # 先保存当前样本的修改
#             save_current_sample(st.session_state.sample_idx)
#             old_idx = st.session_state.sample_idx
#             if st.session_state.sample_idx > 0:
#                 st.session_state.sample_idx -= 1
#                 # 清理旧样本的 widget 状态，避免切换时的状态冲突
#                 clear_sample_widgets(old_idx)
#             st.rerun()

#     # 下一条
#     with col_nav3:
#         if st.button("下一条 ➡️", use_container_width=True):
#             # 先保存当前样本的修改
#             save_current_sample(st.session_state.sample_idx)
#             old_idx = st.session_state.sample_idx
#             if st.session_state.sample_idx < n_samples - 1:
#                 st.session_state.sample_idx += 1
#                 # 清理旧样本的 widget 状态，避免切换时的状态冲突
#                 clear_sample_widgets(old_idx)
#             st.rerun()

#     # 跳转
#     with col_nav2:
#         cur = st.session_state.sample_idx + 1
#         new_idx_display = st.number_input(
#             "跳转到第几条（1-based）",
#             min_value=1,
#             max_value=n_samples,
#             value=cur,
#             step=1,
#         )
#         if new_idx_display != cur:
#             # 先保存当前样本的修改
#             save_current_sample(st.session_state.sample_idx)
#             old_idx = st.session_state.sample_idx
#             st.session_state.sample_idx = new_idx_display - 1
#             # 清理旧样本的 widget 状态，避免切换时的状态冲突
#             clear_sample_widgets(old_idx)
#             st.rerun()

#     st.markdown("---")

#     # 显示当前样本并允许编辑
#     display_sample(st.session_state.sample_idx)

#     # 保存按钮（只在内存中保存，不写磁盘）
#     if st.button("✅ 保存当前样本修改"):
#         save_current_sample(st.session_state.sample_idx)
#         st.success("当前样本已保存到当前会话的内存中。")

#     st.markdown("---")
#     st.subheader("📥 导出标注结果")

#     # 导出前，确保当前样本写回
#     save_current_sample(st.session_state.sample_idx)

#     # 整个数据集导出
#     clean_data = get_clean_data_for_export()
#     json_str = json.dumps(clean_data, ensure_ascii=False, indent=2)
#     download_filename = (
#         (st.session_state.uploaded_name or "labeled_data.json").replace(".json", "")
#         + "_labeled.json"
#     )

#     st.download_button(
#         "⬇️ 下载标注后的 JSON 文件",
#         data=json_str.encode("utf-8"),
#         file_name=download_filename,
#         mime="application/json",
#     )

#     st.caption("提示：下载的是当前会话内存中的全部样本，包括你已经修改保存的内容。")


# if __name__ == "__main__":
#     main()

import json
import streamlit as st

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
