"""
Storyboard PDF Exporter
Generates beautifully formatted PDF from storyboard prompts
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

# Register Chinese font
def register_chinese_font():
    """Register Chinese font for PDF"""
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",      # Microsoft YaHei
        "C:/Windows/Fonts/simsun.ttc",    # SimSun
        "C:/Windows/Fonts/simhei.ttf",    # SimHei
    ]

    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                return 'ChineseFont'
            except:
                continue

    # Fallback
    return 'Helvetica'

# Storyboard data for Episode 1
STORYBOARD_DATA = [
    {
        "shot_number": 1,
        "title": "停车场全景",
        "subject": "停车场环境、男主车辆",
        "shot_type": "远景 - 深夜停车场全貌，男主的车停在角落，车窗已被砸碎",
        "atmosphere": "冷色、压抑、紧张",
        "environment": "深夜地下停车场，昏暗灯光，零星车辆",
        "camera_movement": "缓慢推进，从停车场入口推向男主车辆",
        "angle": "高角度俯拍",
        "special_technique": "航拍或高机位，强调环境压迫感",
        "composition": "远景",
        "style": "电影质感、低饱和度、冷色调",
        "dynamic_control": "静态环境，只有闪烁的灯光",
        "dialogue": "无"
    },
    {
        "shot_number": 2,
        "title": "车窗碎裂特写",
        "subject": "被砸碎的车窗、玻璃碎片",
        "shot_type": "特写 - 车窗破碎的细节，玻璃碎片散落",
        "atmosphere": "冷色、紧张",
        "environment": "车辆侧面",
        "camera_movement": "固定，轻微手持晃动",
        "angle": "平视，正对车窗",
        "special_technique": "浅景深，聚焦碎裂纹理",
        "composition": "特写",
        "style": "电影质感、高对比度",
        "dynamic_control": "静态，偶尔有玻璃碎片滑落",
        "dialogue": "无"
    },
    {
        "shot_number": 3,
        "title": "男主发现车辆",
        "subject": "男主",
        "shot_type": "中景 - 男主走向车辆，发现车窗被砸，身体僵住",
        "atmosphere": "冷色、震惊",
        "environment": "停车场，男主身后是入口方向",
        "camera_movement": "第1个跟拍男主走近，切镜第2个男主正面表情震惊，切镜第3个男主手部握紧",
        "angle": "第1个背部跟拍，第2个正面平视，第3个手部特写",
        "special_technique": "切镜、跟拍转固定",
        "composition": "中景切近景切特写",
        "style": "电影质感、冷色调",
        "dynamic_control": "男主脚步从正常到停顿，身体僵直",
        "dialogue": "男主: \"什么...?\""
    },
    {
        "shot_number": 4,
        "title": "车内物品散落",
        "subject": "车内物品、重要文件",
        "shot_type": "近景 - 车内被翻乱，文件散落一地",
        "atmosphere": "冷色、混乱",
        "environment": "车内",
        "camera_movement": "缓慢横移，展示车内混乱状态",
        "angle": "从车窗外向内拍摄",
        "special_technique": "浅景深，聚焦散落物品",
        "composition": "近景",
        "style": "电影质感",
        "dynamic_control": "静态",
        "dialogue": "无"
    },
    {
        "shot_number": 5,
        "title": "男主愤怒反应",
        "subject": "男主",
        "shot_type": "近景 - 男主愤怒的表情，拳头握紧",
        "atmosphere": "冷色转暖色、愤怒",
        "environment": "停车场，车辆旁",
        "camera_movement": "第1个男主面部愤怒，切镜第2个拳头握紧，切镜第3个男主踢车轮",
        "angle": "第1个正面特写，第2个手部特写，第3个侧面中景",
        "special_technique": "切镜、情绪递进",
        "composition": "特写切特写切中景",
        "style": "电影质感、对比度增强",
        "dynamic_control": "男主情绪爆发，动作激烈",
        "dialogue": "男主: \"到底是谁干的！\""
    },
    {
        "shot_number": 6,
        "title": "保安室场景",
        "subject": "男主、保安",
        "shot_type": "中景 - 男主在保安室询问监控",
        "atmosphere": "中性色调、紧张",
        "environment": "保安室，有监控屏幕",
        "camera_movement": "固定机位，偶尔切换角度",
        "angle": "平视，过肩镜头",
        "special_technique": "过肩镜头对话",
        "composition": "中景",
        "style": "写实风格",
        "dynamic_control": "对话场景，人物表情变化",
        "dialogue": "男主: \"能调一下监控吗？\"\n保安: \"监控...那个区域刚好坏了。\""
    },
    {
        "shot_number": 7,
        "title": "男主怀疑表情",
        "subject": "男主",
        "shot_type": "特写 - 男主听到监控坏了后的怀疑表情",
        "atmosphere": "冷色、怀疑",
        "environment": "保安室",
        "camera_movement": "缓推至大特写",
        "angle": "正面平视",
        "special_technique": "缓推强调情绪",
        "composition": "特写渐变大特写",
        "style": "电影质感",
        "dynamic_control": "男主眼神变化，从愤怒到怀疑",
        "dialogue": "男主(内心独白): \"太巧了吧...\""
    },
    {
        "shot_number": 8,
        "title": "男主离开保安室",
        "subject": "男主",
        "shot_type": "中景 - 男主转身离开保安室，背影坚定",
        "atmosphere": "冷色",
        "environment": "保安室门口",
        "camera_movement": "固定，目送男主离开",
        "angle": "背部中景",
        "special_technique": "固定机位",
        "composition": "中景",
        "style": "电影质感",
        "dynamic_control": "男主快步离开",
        "dialogue": "无"
    },
    {
        "shot_number": 9,
        "title": "电话场景",
        "subject": "男主、手机",
        "shot_type": "近景 - 男主拿出手机准备打电话",
        "atmosphere": "冷色、决绝",
        "environment": "停车场走廊",
        "camera_movement": "第1个男主拿出手机，切镜第2个手机屏幕显示联系人",
        "angle": "第1个侧面近景，第2个手机屏幕特写",
        "special_technique": "切镜",
        "composition": "近景切特写",
        "style": "电影质感",
        "dynamic_control": "男主手指在屏幕上滑动",
        "dialogue": "无"
    },
    {
        "shot_number": 10,
        "title": "女主办公室",
        "subject": "女主（前妻）",
        "shot_type": "远景转中景 - 高档办公室，女主坐在办公桌前",
        "atmosphere": "暖色、高级感",
        "environment": "豪华总裁办公室，落地窗外是城市夜景",
        "camera_movement": "从窗外推入，到女主办公桌",
        "angle": "由高角度转平视",
        "special_technique": "航拍转室内跟拍",
        "composition": "远景转中景",
        "style": "电影质感、暖色调",
        "dynamic_control": "女主优雅地处理文件",
        "dialogue": "无"
    },
    {
        "shot_number": 11,
        "title": "女主接电话",
        "subject": "女主、手机",
        "shot_type": "近景 - 女主看到来电显示，犹豫片刻后接起",
        "atmosphere": "暖色转冷色、复杂情绪",
        "environment": "办公室",
        "camera_movement": "第1个手机响起，切镜第2个女主表情犹豫，切镜第3个女主接起电话",
        "angle": "第1个手机特写，第2个女主正面特写，第3个侧面近景",
        "special_technique": "切镜、表情递进",
        "composition": "特写切特写切近景",
        "style": "电影质感",
        "dynamic_control": "女主从犹豫到决定接听",
        "dialogue": "女主: \"喂？\""
    },
    {
        "shot_number": 12,
        "title": "电话对话-男主",
        "subject": "男主",
        "shot_type": "近景 - 男主打电话，表情复杂",
        "atmosphere": "冷色、压抑",
        "environment": "停车场",
        "camera_movement": "固定，轻微手持",
        "angle": "侧面近景",
        "special_technique": "浅景深",
        "composition": "近景",
        "style": "电影质感、冷色调",
        "dynamic_control": "男主说话时表情变化",
        "dialogue": "男主: \"是你让人砸的我的车吗？\""
    },
    {
        "shot_number": 13,
        "title": "电话对话-女主反应",
        "subject": "女主",
        "shot_type": "特写 - 女主听到指控后的震惊和愤怒",
        "atmosphere": "冷色、愤怒",
        "environment": "办公室",
        "camera_movement": "缓推至大特写",
        "angle": "正面特写",
        "special_technique": "缓推强调情绪",
        "composition": "特写渐变大特写",
        "style": "电影质感",
        "dynamic_control": "女主表情从震惊到愤怒",
        "dialogue": "女主: \"你说什么？你以为我是那种人？！\""
    },
    {
        "shot_number": 14,
        "title": "双人分屏对话",
        "subject": "男主、女主",
        "shot_type": "分屏 - 同时展示两人通话状态",
        "atmosphere": "冷色、对峙",
        "environment": "左：停车场 / 右：办公室",
        "camera_movement": "两边同时缓慢推进",
        "angle": "两人都是正面特写",
        "special_technique": "分屏对话、同步推进",
        "composition": "分屏特写",
        "style": "电影质感、分屏效果",
        "dynamic_control": "两人情绪同时升级",
        "dialogue": "男主: \"除了你还有谁！\"\n女主: \"陈默！我们已经离婚了！你不要再来烦我！\""
    },
    {
        "shot_number": 15,
        "title": "女主挂断电话",
        "subject": "女主",
        "shot_type": "中景 - 女主愤怒地挂断电话，将手机扔在桌上",
        "atmosphere": "冷色、愤怒转失落",
        "environment": "办公室",
        "camera_movement": "第1个女主挂断电话，切镜第2个手机被扔在桌上，切镜第3个女主靠在椅背上",
        "angle": "第1个正面中景，第2个桌面特写，第3个侧面中景",
        "special_technique": "切镜、情绪转变",
        "composition": "中景切特写切中景",
        "style": "电影质感",
        "dynamic_control": "女主从愤怒到疲惫",
        "dialogue": "女主(轻声): \"为什么...还要这样...\""
    },
    {
        "shot_number": 16,
        "title": "男主独自站立",
        "subject": "男主",
        "shot_type": "远景 - 男主独自站在停车场，手机垂在身侧",
        "atmosphere": "冷色、孤独",
        "environment": "空旷的停车场",
        "camera_movement": "缓慢拉远",
        "angle": "高角度俯拍",
        "special_technique": "拉远镜头强调孤独感",
        "composition": "中景拉至远景",
        "style": "电影质感、低饱和度",
        "dynamic_control": "男主静止不动，像雕塑一样",
        "dialogue": "男主(内心独白): \"离婚后...我们就真的成陌生人了吗...\""
    },
    {
        "shot_number": 17,
        "title": "结尾-城市夜景",
        "subject": "城市夜景、两栋建筑",
        "shot_type": "大远景 - 城市夜景，男主所在的停车场和女主所在的写字楼遥遥相望",
        "atmosphere": "冷色、孤寂",
        "environment": "城市全景，夜晚",
        "camera_movement": "航拍，缓慢上升",
        "angle": "高空俯瞰",
        "special_technique": "航拍、象征性构图",
        "composition": "大远景",
        "style": "电影质感、冷色调",
        "dynamic_control": "城市灯光闪烁，车流移动",
        "dialogue": "无"
    },
    {
        "shot_number": 18,
        "title": "第一集结束画面",
        "subject": "字幕卡",
        "shot_type": "黑屏 - 出现第一集结束字幕",
        "atmosphere": "中性",
        "environment": "黑色背景",
        "camera_movement": "固定",
        "angle": "正面",
        "special_technique": "淡入淡出",
        "composition": "居中构图",
        "style": "简洁字幕风格",
        "dynamic_control": "文字淡入",
        "dialogue": "字幕: \"第一集 完\""
    }
]


def create_styles(font_name):
    """Create PDF styles"""
    styles = getSampleStyleSheet()

    # Title style
    styles.add(ParagraphStyle(
        name='ChineseTitle',
        fontName=font_name,
        fontSize=24,
        leading=30,
        alignment=1,  # Center
        spaceAfter=20,
        textColor=colors.HexColor('#1a1a2e')
    ))

    # Subtitle style
    styles.add(ParagraphStyle(
        name='ChineseSubtitle',
        fontName=font_name,
        fontSize=14,
        leading=18,
        alignment=1,
        spaceAfter=30,
        textColor=colors.HexColor('#666666')
    ))

    # Shot header style
    styles.add(ParagraphStyle(
        name='ShotHeader',
        fontName=font_name,
        fontSize=14,
        leading=18,
        spaceAfter=10,
        spaceBefore=15,
        textColor=colors.HexColor('#0071e3'),
        borderColor=colors.HexColor('#0071e3'),
        borderWidth=1,
        borderPadding=5,
        backColor=colors.HexColor('#f0f8ff')
    ))

    # Field label style
    styles.add(ParagraphStyle(
        name='FieldLabel',
        fontName=font_name,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#333333'),
        fontWeight='bold'
    ))

    # Field value style
    styles.add(ParagraphStyle(
        name='FieldValue',
        fontName=font_name,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#555555'),
        leftIndent=10
    ))

    # Dialogue style
    styles.add(ParagraphStyle(
        name='Dialogue',
        fontName=font_name,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#8B0000'),
        leftIndent=10,
        backColor=colors.HexColor('#fff5f5'),
        borderPadding=5
    ))

    return styles


def create_shot_table(shot_data, styles, font_name):
    """Create a table for a single shot"""

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

        # Special styling for dialogue
        if label == "台词" and value != "无":
            value_para = Paragraph(value.replace("\n", "<br/>"), styles['Dialogue'])
        else:
            value_para = Paragraph(value, styles['FieldValue'])

        table_data.append([label_para, value_para])

    table = Table(table_data, colWidths=[80, 400])
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (0, -1), 5),
        ('RIGHTPADDING', (1, 0), (1, -1), 5),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
    ]))

    return table


def generate_pdf(output_filename=None):
    """Generate the storyboard PDF"""

    # Register font
    font_name = register_chinese_font()

    # Create output filename
    if not output_filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"storyboard_ep1_{timestamp}.pdf"

    output_path = OUTPUT_DIR / output_filename

    # Create document
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )

    # Create styles
    styles = create_styles(font_name)

    # Build content
    story = []

    # Title page
    story.append(Spacer(1, 50*mm))
    story.append(Paragraph("分镜脚本", styles['ChineseTitle']))
    story.append(Paragraph("离婚后躺女总裁床上，前妻急了？", styles['ChineseSubtitle']))
    story.append(Paragraph("第一集：停车场车窗被砸 至 结束", styles['ChineseSubtitle']))
    story.append(Spacer(1, 20*mm))
    story.append(Paragraph(f"生成日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['ChineseSubtitle']))
    story.append(Paragraph("共 18 个分镜", styles['ChineseSubtitle']))
    story.append(PageBreak())

    # Shot pages
    for i, shot in enumerate(STORYBOARD_DATA):
        # Shot header
        header_text = f"=== 分镜 {shot['shot_number']} === {shot['title']}"
        story.append(Paragraph(header_text, styles['ShotHeader']))
        story.append(Spacer(1, 5*mm))

        # Shot content table
        table = create_shot_table(shot, styles, font_name)
        story.append(table)

        # Add space or page break
        if i < len(STORYBOARD_DATA) - 1:
            if (i + 1) % 3 == 0:
                story.append(PageBreak())
            else:
                story.append(Spacer(1, 10*mm))

    # Build PDF
    doc.build(story)

    print(f"PDF generated: {output_path}")
    return str(output_path)


if __name__ == "__main__":
    output_path = generate_pdf()
    print(f"\nStoryboard PDF saved to: {output_path}")
