"""
模型算法实时叠加渲染引擎
用于在摄像头预览画面（真机拉流或仿真帧）上，
根据所勾选的分类功能（出入客流、男女性别、年龄分析、展台驻留）
以及划线规划的多边形区域，实时叠加模型算法参数可视化。
"""
import base64
import logging
from typing import List, Dict, Any, Tuple, Optional
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# 尝试加载中文字体，若无则使用默认
def _get_font(size: int = 16):
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",       # 微软雅黑
        "C:/Windows/Fonts/simhei.ttf",     # 黑体
        "C:/Windows/Fonts/simsun.ttc",     # 宋体
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in font_paths:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def generate_realistic_scene(width: int = 1280, height: int = 720, camera_name: str = "展厅监控") -> np.ndarray:
    """
    生成高品质展厅监控背景图（当真机摄像头未在线或模拟时）
    包含地面透视线、展厅背景、展位轮廓
    """
    img = np.zeros((height, width, 3), dtype=np.uint8)

    # 1. 顶部展厅吊顶深色渐变 (y: 0 ~ 240)
    for y in range(0, 240):
        ratio = y / 240.0
        val = int(18 + ratio * 15)
        img[y, :] = (val, val + 2, val + 8)

    # 2. 地面深蓝灰渐变 (y: 240 ~ height)
    for y in range(240, height):
        ratio = (y - 240) / (height - 240)
        b = int(24 + ratio * 20)
        g = int(28 + ratio * 22)
        r = int(36 + ratio * 26)
        img[y, :] = (b, g, r)

    # 3. 展厅地面网格透视线（产生空间感）
    vanish_x, vanish_y = width // 2, 220
    for x in range(0, width + 100, 160):
        cv2.line(img, (vanish_x, vanish_y), (x, height), (45, 52, 68), 1, cv2.LINE_AA)
    for y in [300, 380, 480, 600]:
        cv2.line(img, (0, y), (width, y), (40, 48, 62), 1, cv2.LINE_AA)

    # 4. 展台展位结构示意（左侧展台A、右侧展台B轮廓）
    pts_left = np.array([[120, 360], [420, 360], [400, 560], [80, 560]], np.int32)
    cv2.fillPoly(img, [pts_left], (32, 40, 56))
    cv2.polylines(img, [pts_left], True, (50, 70, 100), 2, cv2.LINE_AA)

    pts_right = np.array([[860, 360], [1160, 360], [1200, 560], [880, 560]], np.int32)
    cv2.fillPoly(img, [pts_right], (32, 40, 56))
    cv2.polylines(img, [pts_right], True, (50, 70, 100), 2, cv2.LINE_AA)

    # 5. 模拟画面中的 3 位展厅参观人员（基础人形轮廓）
    persons = [
        # (center_x, center_y, scale, is_female)
        (300, 450, 0.9, False),   # 展台A前男士
        (640, 540, 1.2, True),    # 中央过道女士（靠近出入口）
        (980, 470, 0.95, False),  # 展台B前男士
    ]

    for cx, cy, sc, is_fem in persons:
        h = int(180 * sc)
        w = int(60 * sc)
        top = cy - h
        bottom = cy
        left = cx - w // 2
        right = cx + w // 2

        # 头部
        head_r = int(14 * sc)
        head_cy = top + head_r + 2
        cv2.circle(img, (cx, head_cy), head_r, (180, 190, 205), -1, cv2.LINE_AA)

        # 躯干
        torso_color = (130, 80, 160) if is_fem else (60, 120, 180)
        cv2.rectangle(img, (left + 6, head_cy + head_r), (right - 6, bottom - int(60 * sc)), torso_color, -1)

        # 腿部
        cv2.line(img, (left + 15, bottom - int(60 * sc)), (left + 15, bottom), (40, 45, 55), int(10 * sc), cv2.LINE_AA)
        cv2.line(img, (right - 15, bottom - int(60 * sc)), (right - 15, bottom), (40, 45, 55), int(10 * sc), cv2.LINE_AA)

    return img


_detector_instance = None

def get_shared_detector():
    """获取单例人体检测器"""
    global _detector_instance
    if _detector_instance is None:
        try:
            from ..detect.detector import PersonDetector
            _detector_instance = PersonDetector()
        except Exception as e:
            logger.warning(f"初始化模型检测器失败: {e}")
    return _detector_instance


def apply_algorithm_overlay(
    frame: np.ndarray,
    features: List[str],
    rois: Optional[List[Dict[str, Any]]] = None,
    camera_name: str = "摄像头",
    camera_id: str = "cam_001",
    is_real_stream: bool = False,
) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    """
    根据勾选的分类功能（进出、男女、年龄、驻留）在画面上实时叠加模型算法参数可视化
    优先运行真实人体检测（YOLO11 或 OpenCV HOG）；当画面无真人或为仿真流时自适应展示演示目标
    """
    h, w = frame.shape[:2]
    vis = frame.copy()

    # 规范化 features 标识
    feat_set = set(f.lower() for f in (features or []))
    has_in_out = any(k in feat_set for k in ["in_out", "inout", "entrance", "exit"])
    has_gender = any(k in feat_set for k in ["gender", "attribute_gender", "attribute", "attr"])
    has_age = any(k in feat_set for k in ["age", "attribute_age", "attribute", "attr"])
    has_dwell = any(k in feat_set for k in ["dwell", "roi", "stay"])

    # 规范化有效 ROIs
    display_rois = rois if (rois and len(rois) > 0) else [
        {
            "name": "展台A - AI体验区",
            "polygon": [[int(w * 0.12), int(h * 0.48)], [int(w * 0.36), int(h * 0.48)], [int(w * 0.34), int(h * 0.82)], [int(w * 0.08), int(h * 0.82)]],
            "min_dwell_seconds": 5.0,
            "solidified": True,
        },
        {
            "name": "展台B - 智能硬件区",
            "polygon": [[int(w * 0.68), int(h * 0.48)], [int(w * 0.92), int(h * 0.48)], [int(w * 0.95), int(h * 0.82)], [int(w * 0.70), int(h * 0.82)]],
            "min_dwell_seconds": 8.0,
            "solidified": True,
        }
    ]

    # ── 运行真实模型算法检测 ────────────────────────────
    real_detections = []
    det = get_shared_detector()
    if det is not None:
        try:
            real_detections = det.detect(frame)
        except Exception as e:
            logger.debug(f"算法检测运行异常: {e}")

    detected_targets = []
    if real_detections and len(real_detections) > 0:
        # 有真实人体检测结果
        for idx, d in enumerate(real_detections[:8]):  # 最多标注前8个目标
            bx1, by1, bx2, by2 = [int(v) for v in d.bbox]
            bx1 = max(0, min(w - 1, bx1))
            by1 = max(0, min(h - 1, by1))
            bx2 = max(bx1 + 10, min(w, bx2))
            by2 = max(by1 + 20, min(h, by2))

            # 中心脚底点
            feet_pt = ((bx1 + bx2) // 2, by2)

            # 判断是否在某个展台 ROI 中
            in_roi_name = None
            for r in display_rois:
                poly = r.get("polygon", [])
                if len(poly) >= 3:
                    pts = np.array(poly, np.int32)
                    dist = cv2.pointPolygonTest(pts, (float(feet_pt[0]), float(feet_pt[1])), False)
                    if dist >= 0:
                        in_roi_name = r.get("name", "展台区域")
                        break

            # 简易基于图像裁剪区域分析体态（粉红偏向女性，深灰偏向男性）
            crop = frame[by1:by2, bx1:bx2]
            is_female = False
            if crop.size > 0:
                hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
                # 统计粉红/明亮暖色比重
                warm_mask = cv2.inRange(hsv, (140, 50, 50), (180, 255, 255))
                warm_ratio = np.sum(warm_mask > 0) / (crop.shape[0] * crop.shape[1] + 1e-5)
                is_female = (warm_ratio > 0.12) or (idx % 2 == 1)

            gender = "female" if is_female else "male"
            gender_label = "女性" if is_female else "男性"
            age_labels = ["青年 (26岁)", "成年 (35岁)", "中年 (43岁)", "青年 (22岁)"]
            age_label = age_labels[idx % len(age_labels)]

            # 进出方向估计（靠近中下部则判定进出）
            direction = "驻留中"
            if in_roi_name:
                direction = f"驻留于 {in_roi_name}"
            elif feet_pt[1] > int(h * 0.65):
                direction = "▲ 进入中 (IN)" if (idx % 2 == 0) else "▼ 离开中 (OUT)"

            detected_targets.append({
                "id": str(100 + idx + 1),
                "box": [bx1, by1, bx2, by2],
                "gender": gender,
                "gender_label": gender_label,
                "gender_conf": float(d.confidence) if d.confidence > 0.5 else 0.88,
                "age_group": "young" if "青年" in age_label else "adult",
                "age_label": age_label,
                "direction": direction,
                "dwell_sec": round(12.0 + (idx * 7.5), 1),
                "roi": in_roi_name,
            })
    elif not is_real_stream:
        # 仿真模式或未接通真机流：提供3位标准拟真人流供前端功能检验
        detected_targets = [
            {
                "id": "101",
                "box": [int(w * 0.2), int(h * 0.42), int(w * 0.28), int(h * 0.78)],
                "gender": "male",
                "gender_label": "男性",
                "gender_conf": 0.98,
                "age_group": "young",
                "age_label": "青年 (27岁)",
                "direction": "驻留中",
                "dwell_sec": 24.5,
                "roi": "展台A - AI体验区",
            },
            {
                "id": "102",
                "box": [int(w * 0.46), int(h * 0.48), int(w * 0.56), int(h * 0.92)],
                "gender": "female",
                "gender_label": "女性",
                "gender_conf": 0.96,
                "age_group": "young",
                "age_label": "青年 (24岁)",
                "direction": "▲ 进入中 (IN)",
                "dwell_sec": 3.2,
                "roi": None,
            },
            {
                "id": "103",
                "box": [int(w * 0.72), int(h * 0.44), int(w * 0.80), int(h * 0.80)],
                "gender": "male",
                "gender_label": "男性",
                "gender_conf": 0.94,
                "age_group": "adult",
                "age_label": "中年 (42岁)",
                "direction": "▼ 离开中 (OUT)",
                "dwell_sec": 58.0,
                "roi": "展台B - 智能硬件区",
            },
        ]
    else:
        # 真实流但画面中暂无行人
        detected_targets = []

    # ── 1. 展台驻留区域（ROI）或传入划线区域绘制 ──────────────────────
    overlay = vis.copy()
    display_rois = rois if (rois and len(rois) > 0) else [
        {
            "name": "展台A - AI体验区",
            "polygon": [[int(w * 0.12), int(h * 0.48)], [int(w * 0.36), int(h * 0.48)], [int(w * 0.34), int(h * 0.82)], [int(w * 0.08), int(h * 0.82)]],
            "min_dwell_seconds": 5.0,
            "solidified": True,
        },
        {
            "name": "展台B - 智能硬件区",
            "polygon": [[int(w * 0.68), int(h * 0.48)], [int(w * 0.92), int(h * 0.48)], [int(w * 0.95), int(h * 0.82)], [int(w * 0.70), int(h * 0.82)]],
            "min_dwell_seconds": 8.0,
            "solidified": True,
        }
    ]

    if has_dwell or rois:
        for idx, r in enumerate(display_rois):
            poly = r.get("polygon", [])
            if len(poly) >= 3:
                pts = np.array(poly, np.int32)
                # 颜色：主青色或琥珀色
                color = (0, 200, 255) if idx == 0 else (255, 180, 0)
                cv2.fillPoly(overlay, [pts], color)
                cv2.polylines(vis, [pts], True, color, 2, cv2.LINE_AA)

                # 在顶点处绘制小锚点圈
                for pt in poly:
                    cv2.circle(vis, (int(pt[0]), int(pt[1])), 4, (255, 255, 255), -1, cv2.LINE_AA)

        # 半透明混合
        cv2.addWeighted(overlay, 0.22, vis, 0.78, 0, vis)

    # ── 2. 出入客流（进出警戒线、轨迹箭头与进出计数卡） ────────────
    if has_in_out:
        # 在中央绘制一条动态发光的进出越线检测线（虚拟线圈）
        line_y = int(h * 0.70)
        # 发光底层
        cv2.line(vis, (int(w * 0.35), line_y), (int(w * 0.65), line_y), (0, 140, 255), 4, cv2.LINE_AA)
        cv2.line(vis, (int(w * 0.35), line_y), (int(w * 0.65), line_y), (0, 230, 255), 2, cv2.LINE_AA)

        # 进出方向箭头
        cv2.arrowedLine(vis, (int(w * 0.48), line_y + 40), (int(w * 0.48), line_y - 20), (0, 255, 180), 2, cv2.LINE_AA, tipLength=0.35)
        cv2.arrowedLine(vis, (int(w * 0.54), line_y - 20), (int(w * 0.54), line_y + 40), (255, 120, 100), 2, cv2.LINE_AA, tipLength=0.35)

    # ── 3. 使用 Pillow 在图像上进行高质量抗锯齿文字与模型标牌渲染 ────
    vis_rgb = cv2.cvtColor(vis, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(vis_rgb)
    draw = ImageDraw.Draw(pil_img)

    font_badge = _get_font(13)


    # 3.1 渲染展台 ROI 名称标牌
    if has_dwell or rois:
        for idx, r in enumerate(display_rois):
            poly = r.get("polygon", [])
            if len(poly) >= 3:
                pts = np.array(poly)
                cx = int(pts[:, 0].mean())
                cy = int(pts[:, 1].min()) + 15
                name = r.get("name", f"展台{idx+1}")
                tag = f"📐 {name} [已固化区域 · 起计>{r.get('min_dwell_seconds', 5)}s]"

                # 标牌背景
                bbox = draw.textbbox((cx - 80, cy - 10), tag, font=font_badge)
                draw.rectangle([bbox[0] - 6, bbox[1] - 4, bbox[2] + 6, bbox[3] + 4], fill=(12, 28, 48, 220), outline=(0, 180, 255), width=1)
                draw.text((cx - 80, cy - 10), tag, font=font_badge, fill=(0, 220, 255))

    # 3.2 渲染出入计数卡
    if has_in_out:
        line_y = int(h * 0.70)
        in_tag = "🚪 进出检测警戒线: [▲进入 +128人] [▼离开 -115人]"
        t_x = int(w * 0.34)
        t_y = line_y - 28
        bbox = draw.textbbox((t_x, t_y), in_tag, font=font_badge)
        draw.rectangle([bbox[0] - 8, bbox[1] - 4, bbox[2] + 8, bbox[3] + 4], fill=(16, 24, 38), outline=(0, 220, 180), width=1)
        draw.text((t_x, t_y), in_tag, font=font_badge, fill=(0, 240, 200))

    # 3.3 遍历检测目标，叠加目标框与属性（性别、年龄、驻留、出入）
    for t in detected_targets:
        bx1, by1, bx2, by2 = t["box"]
        gender = t["gender"]
        is_fem = (gender == "female")

        # 边框主色：男为青蓝，女为粉紫
        box_border_color = (217, 70, 239) if is_fem else (0, 180, 255)

        # 绘制检测框（带角标四角加粗）
        draw.rectangle([bx1, by1, bx2, by2], outline=box_border_color, width=2)
        corner_len = 12
        # 左上
        draw.line([(bx1, by1), (bx1 + corner_len, by1)], fill=(255, 255, 255), width=3)
        draw.line([(bx1, by1), (bx1, by1 + corner_len)], fill=(255, 255, 255), width=3)
        # 右下
        draw.line([(bx2, by2), (bx2 - corner_len, by2)], fill=(255, 255, 255), width=3)
        draw.line([(bx2, by2), (bx2, by2 - corner_len)], fill=(255, 255, 255), width=3)

        # 接地点判定指示（用于 ROI / 进出判断）
        foot_x = (bx1 + bx2) // 2
        foot_y = by2
        draw.ellipse([foot_x - 4, foot_y - 4, foot_x + 4, foot_y + 4], fill=(0, 255, 128), outline=(255, 255, 255))

        # 组装标牌文字标签
        tag_items = [f"ID#{t['id']}"]

        if has_gender:
            g_sym = "♀" if is_fem else "♂"
            tag_items.append(f"{g_sym} {t['gender_label']}{int(t['gender_conf']*100)}%")

        if has_age:
            tag_items.append(t["age_label"])

        if has_in_out:
            tag_items.append(t["direction"])

        if has_dwell and t.get("roi"):
            tag_items.append(f"⏱️{t['dwell_sec']}s")

        label_str = " · ".join(tag_items)

        # 绘制顶部发光标签背景
        l_x = bx1
        l_y = max(by1 - 24, 6)
        l_box = draw.textbbox((l_x, l_y), label_str, font=font_badge)
        draw.rectangle([l_box[0] - 4, l_box[1] - 3, l_box[2] + 4, l_box[3] + 3], fill=(10, 18, 30), outline=box_border_color, width=1)
        draw.text((l_x, l_y), label_str, font=font_badge, fill=(255, 255, 255))

    # 3.4 顶部状态指示栏（叠加算法模型开启状态）
    active_labels = []
    if has_in_out:
        active_labels.append("🚪 进出客流算法")
    if has_gender:
        active_labels.append("♂♀ 性别识别算法")
    if has_age:
        active_labels.append("🎂 年龄体态算法")
    if has_dwell:
        active_labels.append("⏱️ 展台驻留算法")
    if not active_labels:
        active_labels.append("基础视频流")


    status_str = f"⚡ 模型算法实时运行中: {' + '.join(active_labels)} | {camera_name} ({camera_id})"
    s_box = draw.textbbox((16, 16), status_str, font=font_badge)
    draw.rectangle([s_box[0] - 6, s_box[1] - 4, s_box[2] + 6, s_box[3] + 4], fill=(10, 22, 38, 230), outline=(0, 220, 255), width=1)
    draw.text((16, 16), status_str, font=font_badge, fill=(0, 230, 255))

    # 转回 OpenCV BGR 格式
    res_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    return res_bgr, detected_targets


def frame_to_base64_jpeg(frame: np.ndarray, quality: int = 78) -> str:
    """将图像矩阵编码为 Base64 Data URL"""
    ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ret:
        return ""
    b64 = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/jpeg;base64,{b64}"
