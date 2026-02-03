"""
Storyboard PDF Exporter - Episode 1 Full
Based on complete dialogue script
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pathlib import Path
from datetime import datetime
import os

# Output directory
OUTPUT_DIR = Path(__file__).parent / "pdf_outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

def register_chinese_font():
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/simhei.ttf",
    ]
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                return 'ChineseFont'
            except:
                continue
    return 'Helvetica'

# Complete Episode 1 Storyboard Data
STORYBOARD_DATA = [
    # ========== 场景1：江城大学停车场入口 ==========
    {
        "shot_number": 1,
        "title": "停车场入口-宁凡入场",
        "subject": "宁凡、电动车、手机盒",
        "shot_type": "远景转中景 - 夜晚停车场入口，宁凡骑电动车驶入",
        "atmosphere": "暖色、期待、温馨",
        "environment": "江城大学停车场入口，夜晚，路灯昏黄",
        "camera_movement": "从停车场入口远景，缓慢跟拍推进至宁凡中景",
        "angle": "侧面跟拍",
        "special_technique": "跟拍建立环境",
        "composition": "远景转中景",
        "style": "电影质感、暖色调",
        "dynamic_control": "宁凡骑电动车进入，怀里护着手机盒，脸上带着期待的笑容",
        "dialogue": "无"
    },
    {
        "shot_number": 2,
        "title": "宁凡期待表情",
        "subject": "宁凡",
        "shot_type": "近景 - 宁凡脸上带着温暖笑意",
        "atmosphere": "暖色、幸福",
        "environment": "停车场内，背景虚化",
        "camera_movement": "固定跟拍",
        "angle": "侧面近景",
        "special_technique": "浅景深聚焦表情",
        "composition": "近景",
        "style": "电影质感、暖色调",
        "dynamic_control": "宁凡轻轻拍了拍手机盒",
        "dialogue": "宁凡(内心独白): \"三个月，一百二十七单外卖，省下的每一顿饭钱...今天是琪琪二十四岁生日，她一定会喜欢的。\""
    },
    {
        "shot_number": 3,
        "title": "手机盒特写",
        "subject": "手机盒、宁凡的手",
        "shot_type": "特写 - 宁凡怀中的手机盒",
        "atmosphere": "暖色",
        "environment": "电动车上",
        "camera_movement": "固定",
        "angle": "俯拍特写",
        "special_technique": "浅景深",
        "composition": "特写",
        "style": "电影质感",
        "dynamic_control": "宁凡的手轻轻护着盒子",
        "dialogue": "宁凡(内心独白): \"七年了。从高中到现在，我没让她吃过一点苦。她说等毕业就回报我...再熬一熬，好日子就来了。\""
    },

    # ========== 场景2：停车场深处 ==========
    {
        "shot_number": 4,
        "title": "停车场深处-发现异常",
        "subject": "保时捷卡宴",
        "shot_type": "中景 - 停车场深处，一辆保时捷卡宴剧烈摇晃",
        "atmosphere": "冷色、压抑、不安",
        "environment": "停车场深处角落，昏暗灯光",
        "camera_movement": "固定，宁凡主观视角扫过",
        "angle": "主观视角",
        "special_technique": "车窗起雾效果",
        "composition": "中景",
        "style": "电影质感、冷色调",
        "dynamic_control": "保时捷剧烈摇晃，宁凡目光扫过时突然僵住",
        "dialogue": "无"
    },
    {
        "shot_number": 5,
        "title": "发现发卡",
        "subject": "发卡、宁凡",
        "shot_type": "特写转近景 - 后视镜上熟悉的发卡",
        "atmosphere": "冷色、震惊",
        "environment": "保时捷车窗外",
        "camera_movement": "第1个发卡特写，切镜第2个宁凡表情",
        "angle": "第1个特写，第2个正面近景",
        "special_technique": "切镜强调发现",
        "composition": "特写切近景",
        "style": "电影质感",
        "dynamic_control": "宁凡瞳孔收缩",
        "dialogue": "宁凡(内心独白): \"那个发卡...是我用第一份工资买的。她说会一直戴着。\""
    },
    {
        "shot_number": 6,
        "title": "沉重脚步",
        "subject": "宁凡",
        "shot_type": "中景 - 宁凡一步步走近保时捷",
        "atmosphere": "冷色、紧张、痛苦",
        "environment": "停车场",
        "camera_movement": "跟拍，镜头轻微晃动增强不安感",
        "angle": "背部跟拍",
        "special_technique": "手持跟拍",
        "composition": "中景",
        "style": "电影质感、冷色调",
        "dynamic_control": "宁凡的脚像灌了铅，一步步走近",
        "dialogue": "无"
    },
    {
        "shot_number": 7,
        "title": "透过车窗",
        "subject": "车内身影",
        "shot_type": "近景 - 透过起雾的车窗，两个纠缠的身影清晰可辨",
        "atmosphere": "冷色、窒息",
        "environment": "保时捷车窗",
        "camera_movement": "缓慢推进",
        "angle": "宁凡主观视角",
        "special_technique": "起雾效果、朦胧",
        "composition": "近景",
        "style": "电影质感",
        "dynamic_control": "车窗后两个身影纠缠",
        "dialogue": "无"
    },
    {
        "shot_number": 8,
        "title": "认出妻子",
        "subject": "杨琪琪、宁凡",
        "shot_type": "特写对切 - 女人仰起头的瞬间，宁凡认出杨琪琪",
        "atmosphere": "冷色、崩溃",
        "environment": "车窗内外",
        "camera_movement": "第1个车内杨琪琪仰头（模糊），切镜第2个宁凡震惊大特写",
        "angle": "第1个车内，第2个正面大特写",
        "special_technique": "切镜、表情特写",
        "composition": "近景切大特写",
        "style": "电影质感",
        "dynamic_control": "宁凡整个人僵住",
        "dialogue": "宁凡(声音颤抖): \"琪琪...？\""
    },
    {
        "shot_number": 9,
        "title": "回忆闪回-高中送伞",
        "subject": "年轻宁凡、杨琪琪",
        "shot_type": "中景 - 高中雨天，宁凡给杨琪琪送伞",
        "atmosphere": "暖色、温馨",
        "environment": "高中校园，雨天",
        "camera_movement": "固定",
        "angle": "侧面中景",
        "special_technique": "暖黄滤镜、胶片质感、雨景",
        "composition": "中景",
        "style": "回忆风格、暖色调",
        "dynamic_control": "雨中两人相视而笑",
        "dialogue": "无"
    },
    {
        "shot_number": 10,
        "title": "回忆闪回-冬夜外套",
        "subject": "宁凡、杨琪琪",
        "shot_type": "中景 - 冬天把唯一的外套给她",
        "atmosphere": "暖色、感动",
        "environment": "冬夜街头，雪花飘落",
        "camera_movement": "固定",
        "angle": "侧面中景",
        "special_technique": "暖黄滤镜、雪花效果",
        "composition": "中景",
        "style": "回忆风格",
        "dynamic_control": "宁凡脱下外套披在杨琪琪肩上",
        "dialogue": "无"
    },
    {
        "shot_number": 11,
        "title": "回忆闪回-凌晨送外卖",
        "subject": "宁凡",
        "shot_type": "远景 - 凌晨三点，宁凡骑车送外卖",
        "atmosphere": "冷暖交织、辛酸",
        "environment": "凌晨街道，路灯昏暗",
        "camera_movement": "固定远景",
        "angle": "侧面远景",
        "special_technique": "胶片质感",
        "composition": "远景",
        "style": "回忆风格",
        "dynamic_control": "宁凡疲惫地骑车",
        "dialogue": "无"
    },
    {
        "shot_number": 12,
        "title": "回忆闪回-民政局",
        "subject": "宁凡、杨琪琪、结婚证",
        "shot_type": "近景 - 民政局门口，两人手捧红本",
        "atmosphere": "暖色、幸福",
        "environment": "民政局门口，晴天",
        "camera_movement": "固定",
        "angle": "正面近景",
        "special_technique": "暖黄滤镜",
        "composition": "近景",
        "style": "回忆风格",
        "dynamic_control": "杨琪琪笑着挽着宁凡",
        "dialogue": "杨琪琪(回忆): \"这辈子只嫁你一个。\""
    },
    {
        "shot_number": 13,
        "title": "回到现实-七年破碎",
        "subject": "宁凡",
        "shot_type": "大特写 - 宁凡眼中泪光",
        "atmosphere": "冷色、崩溃",
        "environment": "停车场",
        "camera_movement": "缓慢推进",
        "angle": "正面大特写",
        "special_technique": "从暖色回忆切回冷色现实",
        "composition": "大特写",
        "style": "电影质感、强烈对比",
        "dynamic_control": "宁凡眼中的光芒破碎",
        "dialogue": "宁凡(内心独白): \"七年。我的七年。\""
    },
    {
        "shot_number": 14,
        "title": "砸向车窗",
        "subject": "手机盒、车窗",
        "shot_type": "特写 - 宁凡举起手机盒狠狠砸向车窗",
        "atmosphere": "冷色、爆发",
        "environment": "保时捷车窗",
        "camera_movement": "高速摄影（慢动作）",
        "angle": "侧面特写",
        "special_technique": "慢动作、玻璃碎裂",
        "composition": "特写",
        "style": "电影质感、高速摄影",
        "dynamic_control": "手机盒撞击车窗，玻璃碎裂飞溅",
        "dialogue": "(音效): \"哐当！\""
    },

    # ========== 场景3：保时捷车内外 ==========
    {
        "shot_number": 15,
        "title": "车内惊恐",
        "subject": "杨琪琪、陈伟",
        "shot_type": "中景 - 玻璃碎裂，车内两人惊叫着分开",
        "atmosphere": "冷色、混乱",
        "environment": "保时捷车内",
        "camera_movement": "第1个两人惊恐分开，切镜第2个陈伟整理",
        "angle": "车内中景",
        "special_technique": "切镜",
        "composition": "中景切中景",
        "style": "电影质感",
        "dynamic_control": "两人慌乱分开整理衣物",
        "dialogue": "无"
    },
    {
        "shot_number": 16,
        "title": "陈伟嘲讽",
        "subject": "陈伟",
        "shot_type": "中景 - 陈伟手忙脚乱提裤子，看清来人后不屑地笑",
        "atmosphere": "冷色、嚣张",
        "environment": "保时捷车内",
        "camera_movement": "固定",
        "angle": "正面中景",
        "special_technique": "聚焦表情",
        "composition": "中景",
        "style": "电影质感",
        "dynamic_control": "陈伟从慌乱变为不屑",
        "dialogue": "陈伟(不屑地笑): \"我当是谁，原来是杨琪琪那个送快递的老公。\""
    },
    {
        "shot_number": 17,
        "title": "杨琪琪冷漠",
        "subject": "杨琪琪",
        "shot_type": "近景 - 杨琪琪整理衣服，表情从慌乱变得冷漠",
        "atmosphere": "冷色、势利",
        "environment": "保时捷车内",
        "camera_movement": "固定",
        "angle": "正面近景",
        "special_technique": "表情递进",
        "composition": "近景",
        "style": "电影质感",
        "dynamic_control": "杨琪琪冷漠地整理衣服",
        "dialogue": "杨琪琪(冷漠): \"既然你已经看到了，我也没什么好说的。\""
    },
    {
        "shot_number": 18,
        "title": "宁凡质问",
        "subject": "宁凡",
        "shot_type": "近景 - 宁凡声音沙哑地质问",
        "atmosphere": "冷色、悲愤",
        "environment": "车窗外",
        "camera_movement": "固定",
        "angle": "正面近景",
        "special_technique": "聚焦表情",
        "composition": "近景",
        "style": "电影质感",
        "dynamic_control": "宁凡全身颤抖",
        "dialogue": "宁凡(声音沙哑): \"七年。我供你上学七年，你就是这么回报我的？\""
    },
    {
        "shot_number": 19,
        "title": "杨琪琪讽刺",
        "subject": "杨琪琪",
        "shot_type": "近景 - 杨琪琪冷笑",
        "atmosphere": "冷色、讽刺",
        "environment": "车内",
        "camera_movement": "第1个杨琪琪冷笑，切镜第2个瞥向陈伟",
        "angle": "正面近景",
        "special_technique": "切镜",
        "composition": "近景切近景",
        "style": "电影质感",
        "dynamic_control": "杨琪琪眼中是鄙夷",
        "dialogue": "杨琪琪(冷笑): \"回报？宁凡，你看看你自己。一个送快递的，能给我什么？\"\n(瞥了一眼陈伟)\n杨琪琪: \"陈伟一个月的零花钱，够你挣一辈子。\""
    },
    {
        "shot_number": 20,
        "title": "陈伟下车",
        "subject": "陈伟",
        "shot_type": "中景 - 陈伟大笑着走出车门，居高临下",
        "atmosphere": "冷色、嚣张",
        "environment": "保时捷车门旁",
        "camera_movement": "第1个陈伟下车，切镜第2个低角度仰拍",
        "angle": "第1个侧面中景，第2个低角度仰拍",
        "special_technique": "低角度强调压迫感",
        "composition": "中景切仰拍中景",
        "style": "电影质感",
        "dynamic_control": "陈伟拍了拍宁凡的肩膀",
        "dialogue": "陈伟(大笑): \"兄弟，别怪我。你老婆是自己贴上来的。\"\n(拍了拍宁凡肩膀)\n陈伟: \"你一个废物，看见又怎样？\""
    },
    {
        "shot_number": 21,
        "title": "宁凡反击",
        "subject": "宁凡、手机",
        "shot_type": "中景 - 宁凡弯腰捡起砸烂的手机",
        "atmosphere": "冷色、酝酿",
        "environment": "停车场地面",
        "camera_movement": "第1个宁凡弯腰，切镜第2个手部捡手机",
        "angle": "第1个侧面中景，第2个手部特写",
        "special_technique": "切镜",
        "composition": "中景切特写",
        "style": "电影质感",
        "dynamic_control": "宁凡动作缓慢而坚定",
        "dialogue": "无"
    },
    {
        "shot_number": 22,
        "title": "手机砸头",
        "subject": "宁凡、陈伟、手机",
        "shot_type": "中景 - 宁凡猛地抡起手机砸向陈伟的头",
        "atmosphere": "冷色、爆发",
        "environment": "停车场",
        "camera_movement": "高速摄影，第1个挥臂，切镜第2个撞击瞬间",
        "angle": "侧面中景切特写",
        "special_technique": "慢动作、撞击特写",
        "composition": "中景切特写",
        "style": "电影质感、高速摄影",
        "dynamic_control": "手机砸向陈伟额头",
        "dialogue": "(音效): \"砰！\""
    },
    {
        "shot_number": 23,
        "title": "陈伟震惊",
        "subject": "陈伟",
        "shot_type": "近景 - 陈伟捂着流血的额头",
        "atmosphere": "冷色、震惊",
        "environment": "停车场",
        "camera_movement": "固定",
        "angle": "正面近景",
        "special_technique": "血液效果",
        "composition": "近景",
        "style": "电影质感",
        "dynamic_control": "血从指缝流下",
        "dialogue": "陈伟(瞪大眼睛): \"你...你敢打我？！\""
    },
    {
        "shot_number": 24,
        "title": "废物的脾气",
        "subject": "宁凡",
        "shot_type": "特写 - 宁凡坚定的眼神",
        "atmosphere": "冷色、坚定",
        "environment": "停车场",
        "camera_movement": "缓慢推进",
        "angle": "正面特写",
        "special_technique": "缓推强调决心",
        "composition": "特写渐变大特写",
        "style": "电影质感",
        "dynamic_control": "宁凡眼中燃起怒火",
        "dialogue": "宁凡(一字一顿): \"我是废物。但废物也有脾气。\""
    },
    {
        "shot_number": 25,
        "title": "陈伟叫人",
        "subject": "陈伟",
        "shot_type": "近景 - 陈伟疯狂掏手机",
        "atmosphere": "冷色、愤怒",
        "environment": "停车场",
        "camera_movement": "固定",
        "angle": "正面近景",
        "special_technique": "聚焦表情",
        "composition": "近景",
        "style": "电影质感",
        "dynamic_control": "陈伟愤怒地打电话",
        "dialogue": "陈伟(疯狂): \"你知道我爸是谁吗？给我打！往死里打！\""
    },

    # ========== 场景4：停车场 - 围殴 ==========
    {
        "shot_number": 26,
        "title": "打手到场",
        "subject": "黑色轿车、打手",
        "shot_type": "远景 - 三辆黑色轿车呼啸而至",
        "atmosphere": "冷色、压迫",
        "environment": "停车场",
        "camera_movement": "固定，车辆驶入",
        "angle": "远景",
        "special_technique": "车灯光效",
        "composition": "远景",
        "style": "电影质感",
        "dynamic_control": "三辆车快速驶入停下",
        "dialogue": "无"
    },
    {
        "shot_number": 27,
        "title": "打手围住宁凡",
        "subject": "打手、宁凡",
        "shot_type": "中景 - 七八个黑衣打手将宁凡围住",
        "atmosphere": "冷色、绝望",
        "environment": "停车场",
        "camera_movement": "环绕拍摄",
        "angle": "中景环绕",
        "special_technique": "环绕镜头",
        "composition": "中景",
        "style": "电影质感",
        "dynamic_control": "打手们围成一圈",
        "dialogue": "无"
    },
    {
        "shot_number": 28,
        "title": "陈伟踹宁凡",
        "subject": "陈伟、宁凡",
        "shot_type": "中景 - 陈伟一脚踹在宁凡胸口",
        "atmosphere": "冷色、暴力",
        "environment": "停车场",
        "camera_movement": "第1个陈伟踹，切镜第2个宁凡倒地",
        "angle": "侧面中景",
        "special_technique": "动作特写",
        "composition": "中景切中景",
        "style": "电影质感",
        "dynamic_control": "陈伟指着保时捷",
        "dialogue": "陈伟(擦着血): \"一个送快递的，你一年能挣多少钱？\"\n(指着保时捷)\n陈伟: \"我这辆车的一个轮胎，都比你贵！今天让你知道，什么叫天差地别！\""
    },
    {
        "shot_number": 29,
        "title": "围殴",
        "subject": "打手、宁凡",
        "shot_type": "中景转特写 - 打手们拳脚如雨点般落下",
        "atmosphere": "冷色、残酷",
        "environment": "停车场",
        "camera_movement": "第1个群殴全景，切镜第2个宁凡蜷缩，切镜第3个拳头特写",
        "angle": "多角度切换",
        "special_technique": "快速切镜、暴力美学",
        "composition": "中景切近景切特写",
        "style": "电影质感",
        "dynamic_control": "宁凡蜷缩在地，拳头落下",
        "dialogue": "无"
    },
    {
        "shot_number": 30,
        "title": "宁凡倒地视角",
        "subject": "宁凡",
        "shot_type": "近景 - 宁凡蜷缩在地的主观视角",
        "atmosphere": "冷色、绝望",
        "environment": "停车场地面",
        "camera_movement": "手持晃动，模拟被打视角",
        "angle": "低角度主观",
        "special_technique": "主观镜头、晃动",
        "composition": "近景",
        "style": "电影质感",
        "dynamic_control": "画面晃动模糊",
        "dialogue": "宁凡(内心独白): \"原来这就是七年的结局...\""
    },
    {
        "shot_number": 31,
        "title": "望向杨琪琪",
        "subject": "杨琪琪",
        "shot_type": "中景 - 宁凡目光越过人群看向杨琪琪",
        "atmosphere": "冷色、心寒",
        "environment": "停车场",
        "camera_movement": "宁凡主观视角推向杨琪琪",
        "angle": "主观视角",
        "special_technique": "景深变化聚焦杨琪琪",
        "composition": "中景",
        "style": "电影质感",
        "dynamic_control": "杨琪琪冷漠地看着手机",
        "dialogue": "杨琪琪(冷漠地看手机): \"陈伟，差不多行了，别打死了，麻烦。\"\n(头也不回)\n杨琪琪: \"我们走吧。\""
    },
    {
        "shot_number": 32,
        "title": "陈伟离开",
        "subject": "陈伟、杨琪琪",
        "shot_type": "中景 - 陈伟啐了一口，众人离开",
        "atmosphere": "冷色、残酷",
        "environment": "停车场",
        "camera_movement": "固定，目送离开",
        "angle": "中景",
        "special_technique": "脚步声远去",
        "composition": "中景",
        "style": "电影质感",
        "dynamic_control": "陈伟和杨琪琪转身离开",
        "dialogue": "陈伟(啐了一口): \"算你命大。\"\n(脚步声远去)"
    },

    # ========== 场景5：停车场 - 血泊中 ==========
    {
        "shot_number": 33,
        "title": "血泊中的宁凡",
        "subject": "宁凡",
        "shot_type": "远景转近景 - 宁凡躺在血泊中，意识模糊",
        "atmosphere": "冷色、绝望",
        "environment": "空旷的停车场，只有宁凡倒在地上",
        "camera_movement": "缓慢推进",
        "angle": "高角度俯拍转平视",
        "special_technique": "缓推",
        "composition": "远景转近景",
        "style": "电影质感、低饱和度",
        "dynamic_control": "宁凡一动不动躺在血泊中",
        "dialogue": "无"
    },
    {
        "shot_number": 34,
        "title": "玉佩觉醒",
        "subject": "玉佩、宁凡胸口",
        "shot_type": "特写 - 胸口的古玉被鲜血浸透，发出微光",
        "atmosphere": "冷色转神秘光芒",
        "environment": "宁凡胸口",
        "camera_movement": "固定，光芒渐强",
        "angle": "俯拍特写",
        "special_technique": "光效、神秘氛围",
        "composition": "特写",
        "style": "电影质感、神秘效果",
        "dynamic_control": "玉佩被血浸透后开始发光",
        "dialogue": "宁凡(内心独白): \"这玉...是爸留下的...妈说过，关键时刻会保护我...\""
    },
    {
        "shot_number": 35,
        "title": "车灯划破夜空",
        "subject": "车灯光芒",
        "shot_type": "远景 - 一道刺眼的车灯划破夜空",
        "atmosphere": "冷色转希望",
        "environment": "停车场入口",
        "camera_movement": "固定，车灯由远及近",
        "angle": "远景",
        "special_technique": "强光效果",
        "composition": "远景",
        "style": "电影质感",
        "dynamic_control": "车灯光芒照亮黑暗",
        "dialogue": "无"
    },
    {
        "shot_number": 36,
        "title": "帕拉梅拉登场",
        "subject": "保时捷帕拉梅拉",
        "shot_type": "中景 - 白色帕拉梅拉缓缓停下",
        "atmosphere": "神秘、高贵",
        "environment": "停车场",
        "camera_movement": "跟拍车辆停下",
        "angle": "侧面中景",
        "special_technique": "豪车展示",
        "composition": "中景",
        "style": "电影质感",
        "dynamic_control": "豪车缓缓停稳",
        "dialogue": "无"
    },
    {
        "shot_number": 37,
        "title": "江如雪下车",
        "subject": "江如雪",
        "shot_type": "中景 - 车门打开，绝美女人走出",
        "atmosphere": "神秘、高贵、震撼",
        "environment": "帕拉梅拉车旁",
        "camera_movement": "第1个车门打开，切镜第2个高跟鞋落地，切镜第3个全身中景",
        "angle": "多角度展示",
        "special_technique": "慢动作、气场展示",
        "composition": "特写切特写切中景",
        "style": "电影质感",
        "dynamic_control": "江如雪气场让整个停车场都安静了",
        "dialogue": "无"
    },
    {
        "shot_number": 38,
        "title": "打手议论",
        "subject": "打手甲乙",
        "shot_type": "近景 - 还没离开的打手低声议论",
        "atmosphere": "震惊、敬畏",
        "environment": "停车场角落",
        "camera_movement": "固定",
        "angle": "侧面近景",
        "special_technique": "对话镜头",
        "composition": "双人近景",
        "style": "电影质感",
        "dynamic_control": "两人惊讶地看着",
        "dialogue": "打手甲(低声): \"这车...少说四百万...\"\n打手乙: \"什么人？\""
    },
    {
        "shot_number": 39,
        "title": "江如雪走向宁凡",
        "subject": "江如雪、宁凡",
        "shot_type": "中景 - 江如雪目不斜视，径直走向血泊中的宁凡",
        "atmosphere": "神秘、决绝",
        "environment": "停车场",
        "camera_movement": "跟拍江如雪",
        "angle": "侧面跟拍",
        "special_technique": "高跟鞋声音、气场",
        "composition": "中景",
        "style": "电影质感",
        "dynamic_control": "江如雪步伐坚定",
        "dialogue": "无"
    },
    {
        "shot_number": 40,
        "title": "单膝蹲下",
        "subject": "江如雪、宁凡",
        "shot_type": "近景 - 江如雪单膝蹲下，轻声说话",
        "atmosphere": "温柔、神秘",
        "environment": "宁凡身旁",
        "camera_movement": "固定",
        "angle": "侧面近景",
        "special_technique": "柔光",
        "composition": "双人近景",
        "style": "电影质感",
        "dynamic_control": "江如雪蹲在宁凡身旁",
        "dialogue": "江如雪(轻声): \"宁少，老爷子让我来接您回家。\""
    },
    {
        "shot_number": 41,
        "title": "宁凡艰难睁眼",
        "subject": "宁凡",
        "shot_type": "特写 - 宁凡艰难睁眼，看着眼前的女人",
        "atmosphere": "虚弱、疑惑",
        "environment": "地面视角",
        "camera_movement": "固定",
        "angle": "仰视特写",
        "special_technique": "模糊转清晰",
        "composition": "特写",
        "style": "电影质感",
        "dynamic_control": "宁凡挣扎着睁眼",
        "dialogue": "宁凡(艰难睁眼，声音微弱): \"你...是谁...\""
    },
    {
        "shot_number": 42,
        "title": "江如雪微笑",
        "subject": "江如雪",
        "shot_type": "特写 - 江如雪微微一笑",
        "atmosphere": "温柔、神秘",
        "environment": "宁凡视角",
        "camera_movement": "固定",
        "angle": "仰视特写",
        "special_technique": "柔光效果",
        "composition": "特写",
        "style": "电影质感",
        "dynamic_control": "江如雪优雅微笑",
        "dialogue": "江如雪(微微一笑): \"我叫江如雪。从今往后，我是您的人。\""
    },
    {
        "shot_number": 43,
        "title": "江如雪眼神变冷",
        "subject": "江如雪",
        "shot_type": "特写 - 江如雪抬起头，目光扫过远处的陈伟",
        "atmosphere": "冷色、威压",
        "environment": "停车场",
        "camera_movement": "第1个江如雪抬头，切镜第2个眼神特写",
        "angle": "侧面转正面特写",
        "special_technique": "眼神变化",
        "composition": "近景切大特写",
        "style": "电影质感",
        "dynamic_control": "江如雪眼神骤然变冷",
        "dialogue": "江如雪(冷冷地): \"江城陈氏？就凭他们，也敢动您？\""
    },
    {
        "shot_number": 44,
        "title": "宁凡意识陷入黑暗",
        "subject": "宁凡",
        "shot_type": "特写转黑屏 - 宁凡意识陷入黑暗",
        "atmosphere": "黑暗、神秘",
        "environment": "宁凡视角",
        "camera_movement": "画面逐渐变暗",
        "angle": "主观视角",
        "special_technique": "渐暗转场",
        "composition": "特写转黑屏",
        "style": "电影质感",
        "dynamic_control": "视野逐渐模糊变暗",
        "dialogue": "(只听见江如雪拨通电话的声音)"
    },
    {
        "shot_number": 45,
        "title": "江如雪打电话",
        "subject": "江如雪",
        "shot_type": "近景 - 江如雪拨通电话",
        "atmosphere": "冷色、霸气",
        "environment": "停车场",
        "camera_movement": "固定",
        "angle": "侧面近景",
        "special_technique": "声音设计",
        "composition": "近景",
        "style": "电影质感",
        "dynamic_control": "江如雪冷静地打电话",
        "dialogue": "江如雪: \"通知下去。江城，要变天了。\""
    },

    # ========== 结尾 ==========
    {
        "shot_number": 46,
        "title": "结尾画面",
        "subject": "城市夜景",
        "shot_type": "大远景 - 城市夜景，灯火阑珊",
        "atmosphere": "冷色、史诗感",
        "environment": "城市全景",
        "camera_movement": "缓慢拉远至城市全景",
        "angle": "航拍大远景",
        "special_technique": "航拍、配乐渐起",
        "composition": "大远景",
        "style": "电影质感",
        "dynamic_control": "城市灯光闪烁",
        "dialogue": "旁白: \"被踩入泥土的，未必是蝼蚁。有些人坠落尘埃，只是因为还没到腾飞的时候。\""
    },
    {
        "shot_number": 47,
        "title": "第一集完",
        "subject": "字幕卡",
        "shot_type": "黑屏 - 第一集结束字幕",
        "atmosphere": "中性",
        "environment": "黑色背景",
        "camera_movement": "固定",
        "angle": "正面",
        "special_technique": "淡入淡出",
        "composition": "居中构图",
        "style": "简洁字幕风格",
        "dynamic_control": "文字淡入淡出",
        "dialogue": "字幕: \"第一集 完\""
    }
]


def create_styles(font_name):
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name='ChineseTitle',
        fontName=font_name,
        fontSize=26,
        leading=32,
        alignment=1,
        spaceAfter=20,
        textColor=colors.HexColor('#1a1a2e')
    ))

    styles.add(ParagraphStyle(
        name='ChineseSubtitle',
        fontName=font_name,
        fontSize=14,
        leading=18,
        alignment=1,
        spaceAfter=30,
        textColor=colors.HexColor('#666666')
    ))

    styles.add(ParagraphStyle(
        name='ShotHeader',
        fontName=font_name,
        fontSize=13,
        leading=16,
        spaceAfter=8,
        spaceBefore=12,
        textColor=colors.HexColor('#722ed1'),
        borderColor=colors.HexColor('#722ed1'),
        borderWidth=1,
        borderPadding=5,
        backColor=colors.HexColor('#f9f0ff')
    ))

    styles.add(ParagraphStyle(
        name='FieldLabel',
        fontName=font_name,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#333333'),
    ))

    styles.add(ParagraphStyle(
        name='FieldValue',
        fontName=font_name,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#555555'),
        leftIndent=8
    ))

    styles.add(ParagraphStyle(
        name='Dialogue',
        fontName=font_name,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#c41d7f'),
        leftIndent=8,
        backColor=colors.HexColor('#fff0f6'),
        borderPadding=4
    ))

    return styles


def create_shot_table(shot_data, styles, font_name):
    fields = [
        ("主体", shot_data["subject"]),
        ("景别", shot_data["shot_type"]),
        ("氛围", shot_data["atmosphere"]),
        ("环境", shot_data["environment"]),
        ("运镜", shot_data["camera_movement"]),
        ("视角", shot_data["angle"]),
        ("特殊拍摄手法", shot_data["special_technique"]),
        ("构图", shot_data["composition"]),
        ("风格统一", shot_data["style"]),
        ("动态控制", shot_data["dynamic_control"]),
        ("台词", shot_data["dialogue"]),
    ]

    table_data = []
    for label, value in fields:
        label_para = Paragraph(f"<b>{label}:</b>", styles['FieldLabel'])
        if label == "台词" and value != "无":
            value_para = Paragraph(value.replace("\n", "<br/>"), styles['Dialogue'])
        else:
            value_para = Paragraph(value, styles['FieldValue'])
        table_data.append([label_para, value_para])

    table = Table(table_data, colWidths=[75, 405])
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (0, -1), 4),
        ('RIGHTPADDING', (1, 0), (1, -1), 4),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f9f0ff')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d3adf7')),
    ]))

    return table


def generate_pdf(output_filename=None):
    font_name = register_chinese_font()

    if not output_filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"storyboard_ep1_complete_{timestamp}.pdf"

    output_path = OUTPUT_DIR / output_filename

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=18*mm,
        leftMargin=18*mm,
        topMargin=18*mm,
        bottomMargin=18*mm
    )

    styles = create_styles(font_name)
    story = []

    # Title page
    story.append(Spacer(1, 40*mm))
    story.append(Paragraph("分镜脚本", styles['ChineseTitle']))
    story.append(Spacer(1, 10*mm))
    story.append(Paragraph("离婚后躺女总裁床上，前妻急了？", styles['ChineseSubtitle']))
    story.append(Paragraph("第1集《七年深情喂了狗！老婆竟和富二代车震》", styles['ChineseSubtitle']))
    story.append(Spacer(1, 15*mm))
    story.append(Paragraph("场景列表:", styles['ChineseSubtitle']))
    story.append(Paragraph("场景1: 江城大学停车场入口", styles['ChineseSubtitle']))
    story.append(Paragraph("场景2: 停车场深处", styles['ChineseSubtitle']))
    story.append(Paragraph("场景3: 保时捷车内外", styles['ChineseSubtitle']))
    story.append(Paragraph("场景4: 停车场-围殴", styles['ChineseSubtitle']))
    story.append(Paragraph("场景5: 停车场-血泊中", styles['ChineseSubtitle']))
    story.append(Spacer(1, 15*mm))
    story.append(Paragraph(f"生成日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['ChineseSubtitle']))
    story.append(Paragraph(f"共 {len(STORYBOARD_DATA)} 个分镜", styles['ChineseSubtitle']))
    story.append(PageBreak())

    # Shot pages
    for i, shot in enumerate(STORYBOARD_DATA):
        header_text = f"=== 分镜 {shot['shot_number']} === {shot['title']}"
        story.append(Paragraph(header_text, styles['ShotHeader']))
        story.append(Spacer(1, 3*mm))

        table = create_shot_table(shot, styles, font_name)
        story.append(table)

        if i < len(STORYBOARD_DATA) - 1:
            if (i + 1) % 3 == 0:
                story.append(PageBreak())
            else:
                story.append(Spacer(1, 8*mm))

    doc.build(story)
    print(f"PDF generated: {output_path}")
    return str(output_path)


if __name__ == "__main__":
    output_path = generate_pdf()
    print(f"\nStoryboard PDF saved to: {output_path}")
