# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import streamlit as st
import json
import base64
from io import BytesIO
from PIL import Image
import os
import sys
import asyncio
import importlib
import re
from pathlib import Path

# Ensure local imports work
sys.path.append(os.getcwd())

from utils.pipeline_state import (
    build_render_stage_entries,
    detect_task_type_from_result,
    find_final_stage_keys,
    get_available_critic_rounds,
    resolve_stage_artifact_keys,
    stage_display_label,
)
from utils.result_bundle import load_result_bundle
from utils.result_paths import resolve_gt_image_path

st.set_page_config(layout="wide", page_title="PaperBanana 参考评测查看器", page_icon="🍌")


def detect_task_type(data):
    """Detect whether data is for diagram or plot task."""
    return detect_task_type_from_result(data)

@st.cache_data
def load_data(path):
    """Read legacy JSON/JSONL files or standardized result bundles."""
    if not os.path.exists(path):
        return {"manifest": {}, "summary": {}, "failures": [], "results": []}
    try:
        return load_result_bundle(path)
    except Exception as e:
        st.error(f"读取结果文件失败：{e}")
        return {"manifest": {}, "summary": {}, "failures": [], "results": []}

def calculate_stats(data, dimensions):
    """Calculate win rates for each dimension."""
    outcomes = ["Model", "Human", "Both are good", "Both are bad", "Tie", "Error", "Unknown"]
    stats = {dim: {out: 0 for out in outcomes} for dim in dimensions}
    
    for item in data:
        for dim in dimensions:
            outcome = item.get(f"{dim.lower()}_outcome", "Unknown")
            if outcome in outcomes:
                stats[dim][outcome] += 1
            else:
                stats[dim]["Unknown"] += 1
    return stats

def base64_to_image(b64_str):
    if not b64_str:
        return None
    try:
        if "," in b64_str:
            b64_str = b64_str.split(",")[1]
        image_data = base64.b64decode(b64_str)
        return Image.open(BytesIO(image_data))
    except Exception:
        return None

def load_local_image(path):
    if path and os.path.exists(path):
        return Image.open(path)
    return None
def get_latest_critic_keys(item, task_type):
    rounds = get_available_critic_rounds(item, task_type)
    if not rounds:
        return None, None
    final_round = rounds[-1]
    return (
        f"target_{task_type}_critic_desc{final_round}_base64_jpg",
        f"target_{task_type}_critic_desc{final_round}",
    )


def get_display_mode_options(data, task_type):
    ordered_sources = ["vanilla", "planner", "stylist", "critic", "polish"]
    available_sources = []
    seen = set()
    for item in data:
        for stage_entry in build_render_stage_entries(
            item,
            task_type,
            item.get("exp_mode"),
        ):
            stage_name = stage_entry["stage_name"]
            if stage_name in ordered_sources and stage_name not in seen:
                seen.add(stage_name)
                available_sources.append(stage_name)

    labels = ["Auto"]
    source_map = {"Auto": None}
    for source in ordered_sources:
        if source in available_sources:
            label = stage_display_label(source)
            labels.append(label)
            source_map[label] = source
    return labels, source_map

def display_outcome(outcome):
    if outcome == "Model":
        return f":blue[**{outcome}**]"
    if outcome == "Human":
        return f":green[**{outcome}**]"
    if outcome == "Both are good":
        return f":orange[**{outcome}**]"
    if outcome == "Both are bad":
        return f":red[**{outcome}**]"
    if outcome == "Tie":
        return f":violet[**{outcome}**]"
    return f":gray[**{outcome}**]"

def format_reasoning(text):
    """Format reasoning string for better readability in Streamlit."""
    if not text:
        return ""
    
    # Common headers used in prompts
    headers = [
        "Faithfulness of Human", "Faithfulness of Model",
        "Conciseness of Human", "Conciseness of Model",
        "Readability of Human", "Readability of Model",
        "Aesthetics of Human", "Aesthetics of Model",
        "Overall Quality of Human", "Overall Quality of Model",
        "Conclusion"
    ]
    
    formatted_text = text
    # Ensure headers at the start or after a space/punctuation are bolded and preceded by newlines
    for header in headers:
        # Match header followed by colon, case-insensitive
        pattern = re.compile(rf"({re.escape(header)}):", re.IGNORECASE)
        # Use \n\n to ensure a clear paragraph break
        formatted_text = pattern.sub(r"\n\n**\1**:", formatted_text)
    
    # Clean up: remove semicolon if it's right before our new bolded section
    formatted_text = re.sub(r";\s*\n\n", r"\n\n", formatted_text)
    
    # Final trim
    return formatted_text.strip()

async def run_eval_on_sample(sample, task_name="diagram"):
    """Hot-reload prompts and run eval."""
    import prompts.diagram_eval_prompts
    import prompts.plot_eval_prompts
    import utils.eval_toolkits
    
    importlib.reload(prompts.diagram_eval_prompts)
    importlib.reload(prompts.plot_eval_prompts)
    importlib.reload(utils.eval_toolkits)
    from utils.eval_toolkits import get_score_for_image_referenced
    
    # Ensure eval_image_field is set
    if "eval_image_field" not in sample:
        inferred_eval_key, _ = find_final_stage_keys(
            sample,
            task_name,
            sample.get("exp_mode", "demo_planner_critic"),
        )
        sample["eval_image_field"] = inferred_eval_key or "vanilla_image_base64"
    
    return await get_score_for_image_referenced(
        sample,
        task_name=task_name,
        work_dir=Path(os.getcwd()),
    )

def main():
    st.sidebar.title("🍌 参考评测查看器")
    file_path = st.sidebar.text_input("结果文件路径", placeholder="请输入结果文件路径...")
    
    # --- Debug Tool Section in Sidebar ---
    if "debug_sample" in st.session_state:
        st.sidebar.divider()
        st.sidebar.subheader("🛠️ 调试目标")
        debug_sample = st.session_state.debug_sample
        identifier = debug_sample.get('id')
        st.sidebar.info(f"当前样本：{identifier}\n索引：{st.session_state.debug_idx}")
        
        if st.sidebar.button("🚀 重新评测（热加载 Prompt）", type="primary"):
            with st.spinner("正在执行实时评测..."):
                try:
                    # Pass task_name if available
                    task_name = st.session_state.get("task_type", "diagram")
                    new_result = asyncio.run(run_eval_on_sample(debug_sample.copy(), task_name))
                    st.session_state.debug_result = new_result
                    st.sidebar.success("评测完成。")
                except Exception as e:
                    st.sidebar.error(f"评测失败：{e}")
        
        if st.sidebar.button("🧹 清除调试状态"):
            if "debug_sample" in st.session_state: del st.session_state.debug_sample
            if "debug_idx" in st.session_state: del st.session_state.debug_idx
            if "debug_result" in st.session_state: del st.session_state.debug_result
            st.rerun()

    if st.sidebar.button("🔄 刷新数据"):
        load_data.clear()
        st.rerun()

    if not file_path:
        st.info("👆 请输入结果文件路径")
        st.stop()

    if not os.path.exists(file_path):
        st.error(f"未找到文件：{file_path}")
        st.stop()

    bundle = load_data(file_path)
    data = bundle.get("results", [])
    manifest = bundle.get("manifest", {})

    with st.sidebar.expander("🧾 运行清单", expanded=False):
        manifest_fields = [
            ("来源", "producer"),
            ("数据集", "dataset_name"),
            ("任务", "task_name"),
            ("切分", "split_name"),
            ("模式", "exp_mode"),
            ("Provider", "provider"),
            ("文本模型", "model_name"),
            ("图像模型", "image_model_name"),
        ]
        for label, key in manifest_fields:
            value = manifest.get(key)
            if value:
                st.write(f"**{label}:** {value}")
        st.write(f"**结果数：** {manifest.get('result_count', len(data))}")
    
    # Detect task type
    task_type = detect_task_type(data)
    st.session_state["task_type"] = task_type
    display_mode_options, display_mode_source_map = get_display_mode_options(data, task_type)
    display_mode = st.sidebar.selectbox(
        "模型显示阶段",
        display_mode_options,
        help="选择要展示模型输出的哪个阶段。",
    )
    
    # --- Search Functionality ---
    search_field = "id"
    search_query = st.sidebar.text_input(
        f"🔍 搜索 {search_field.upper()}",
        value="",
        help=f"按 {search_field.upper()} 过滤（不区分大小写）",
    )
    if search_query:
        data = [item for item in data if search_query.lower() in str(item.get(search_field, "")).lower()]
        st.sidebar.caption(f"找到 {len(data)} 条匹配结果")

    total_items = len(data)

    if total_items == 0:
        if search_query:
            st.warning(f"没有找到匹配 “{search_query}” 的样本。")
        else:
            st.warning("结果为空，或文件格式不正确。")
        return

    st.title("🍌 参考评测查看器")
    
    # --- Global Stats ---
    dimensions = ["Faithfulness", "Conciseness", "Readability", "Aesthetics", "Overall"]
    stats = calculate_stats(data, dimensions)
    
    with st.expander("📊 全局统计", expanded=False):
        cols = st.columns(len(dimensions))
        for i, dim in enumerate(dimensions):
            with cols[i]:
                st.info(f"**{dim}**")
                s = stats[dim]
                total = sum(s.values()) or 1
                st.metric("模型胜率", f"{(s['Model'])/total:.1%}")
                st.metric("人工胜率", f"{(s['Human'])/total:.1%}")
                st.metric("双方都好", f"{(s['Both are good'])/total:.1%}")
                st.metric("双方都差", f"{(s['Both are bad'])/total:.1%}")
                # Add Tie metric for Overall dimension
                if dim == "Overall":
                    tie_count = s.get("Tie", 0)
                    st.metric("平局", f"{tie_count/total:.1%}")

    st.divider()

    # --- Pagination ---
    PAGE_SIZE = 10
    if "page" not in st.session_state:
        st.session_state.page = 0
    
    total_pages = max((total_items + PAGE_SIZE - 1) // PAGE_SIZE, 1)

    def on_page_change():
        st.session_state.page = st.session_state.page_input - 1

    st.sidebar.number_input(
        "页码", 
        min_value=1, 
        max_value=total_pages, 
        value=st.session_state.page + 1,
        key="page_input",
        on_change=on_page_change
    )
    
    # Ensure page is within valid range (e.g. if search reduced results)
    if st.session_state.page >= total_pages:
        st.session_state.page = total_pages - 1
    
    start_idx = st.session_state.page * PAGE_SIZE
    end_idx = min(start_idx + PAGE_SIZE, total_items)
    batch = data[start_idx:end_idx]
    
    st.sidebar.markdown(f"正在显示第 {start_idx + 1} - {end_idx} 条，共 {total_items} 条")

    for i, item in enumerate(batch):
        idx = start_idx + i
        
        # Extract metadata based on task type
        identifier = item.get("id", "Unknown")
        caption_or_desc = item.get("visual_intent") or item.get("brief_desc", "N/A")
        if task_type == "plot":
            raw_content_label = "原始数据"
            raw_content = json.dumps(item.get("content", {}), indent=2)
        else:  # diagram
            raw_content_label = "方法章节"
            raw_content = item.get("content", "N/A")
        
        is_debugging = "debug_sample" in st.session_state and st.session_state.debug_idx == idx
        
        with st.container(border=is_debugging):
            col_title, col_btn = st.columns([0.8, 0.2])
            with col_title:
                st.subheader(f"#{idx + 1}: {caption_or_desc}")
            with col_btn:
                if st.button("🛠️ 调试", key=f"btn_debug_{idx}"):
                    st.session_state.debug_sample = item
                    st.session_state.debug_idx = idx
                    st.rerun()

            st.caption(f"{search_field.title()}: `{identifier}`")
            
            # --- Determine Image and Text for Model ---
            if display_mode == "Auto":
                model_b64_key, model_text_key = find_final_stage_keys(
                    item,
                    task_type,
                    item.get(
                        "exp_mode",
                        st.session_state.get("exp_mode", "demo_planner_critic"),
                    ),
                )
            else:
                selected_source = display_mode_source_map.get(display_mode)
                if selected_source == "critic":
                    latest_b64_key, latest_text_key = get_latest_critic_keys(item, task_type)
                    if latest_b64_key and latest_text_key:
                        model_b64_key = latest_b64_key
                        model_text_key = latest_text_key
                    else:
                        model_b64_key, model_text_key = find_final_stage_keys(
                            item,
                            task_type,
                            item.get(
                                "exp_mode",
                                st.session_state.get("exp_mode", "demo_planner_critic"),
                            ),
                        )
                else:
                    model_b64_key, model_text_key = resolve_stage_artifact_keys(
                        task_type,
                        selected_source or "planner",
                    )

            model_b64 = item.get(model_b64_key)
            model_description = item.get(model_text_key, "N/A")

            # Outcome Summary
            outcome_cols = st.columns(len(dimensions))
            for j, dim in enumerate(dimensions):
                outcome_cols[j].markdown(f"**{dim}**\n{display_outcome(item.get(f'{dim.lower()}_outcome'))}")

            # Debug Results Overlay
            if is_debugging and "debug_result" in st.session_state:
                st.markdown("---")
                st.markdown("### 🧪 **实时调试结果**（基于当前 Prompt）")
                new_res = st.session_state.debug_result
                new_cols = st.columns(len(dimensions))
                for j, dim in enumerate(dimensions):
                    new_cols[j].markdown(f"**{dim}**\n{display_outcome(new_res.get(f'{dim.lower()}_outcome'))}")
                st.markdown("---")

            # Images
            img_col1, img_col2 = st.columns(2)
            with img_col1:
                model_label = "模型统计图" if task_type == "plot" else "模型图解"
                st.markdown(f"**{model_label}** ({display_mode})")
                if model_b64:
                    st.image(base64_to_image(model_b64), width="stretch")
                else:
                    st.error(f"缺少结果字段：`{model_b64_key}`")
                
                with st.expander("📄 模型描述", expanded=False):
                    st.write(model_description)
            
            with img_col2:
                human_label = "人工统计图" if task_type == "plot" else "人工图解"
                st.markdown(f"**{human_label}**（人工参考）")
                
                # Get GT image path based on task type
                if task_type == "plot":
                    gt_path = item.get("path_to_gt_image")
                else:
                    gt_path = item.get("path_to_gt_image")
                
                resolved_gt_path = resolve_gt_image_path(
                    gt_path,
                    task_type,
                    file_path,
                    work_dir=os.getcwd(),
                    dataset_name=item.get("dataset_name"),
                )
                gt_img = load_local_image(str(resolved_gt_path) if resolved_gt_path else None)
                if gt_img:
                    st.image(gt_img, width="stretch")
                else:
                    st.error(f"未找到人工参考图：{resolved_gt_path}")
                
                with st.expander("📄 人工图与图注信息", expanded=False):
                    st.markdown(f"**图注/说明：** {caption_or_desc}")
                    if task_type == "diagram":
                        st.markdown(f"**人工图解说明：** {item.get('gt_diagram_desc0', 'N/A')}")
            
            # Suggestions (if any)
            suggestions = item.get("suggestions_diagram") or item.get("suggestions_plot")
            if suggestions:
                with st.expander("💡 精修建议", expanded=False):
                    st.markdown(suggestions)
            
            # Raw Content Section - spans full width
            with st.expander(f"📚 {raw_content_label}", expanded=False):
                if task_type == "plot":
                    st.code(raw_content, language="json")
                else:
                    st.markdown(raw_content)

            # Reasoning
            with st.expander("📝 原始评测理由", expanded=False):
                tabs = st.tabs(dimensions)
                for tab, dim in zip(tabs, dimensions):
                    with tab:
                        reasoning = item.get(f"{dim.lower()}_reasoning", "未提供理由。")
                        st.markdown(format_reasoning(reasoning))

            if is_debugging and "debug_result" in st.session_state:
                with st.expander("🧪 调试理由（当前 Prompt）", expanded=True):
                    new_res = st.session_state.debug_result
                    tabs = st.tabs(dimensions)
                    for tab, dim in zip(tabs, dimensions):
                        with tab:
                            reasoning = new_res.get(f"{dim.lower()}_reasoning", "N/A")
                            st.markdown(format_reasoning(reasoning))
            
            st.divider()

if __name__ == "__main__":
    main()

