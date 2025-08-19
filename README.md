# Dota 2 经济优势与胜率分析工具 ( **Dota-2-Advantage-Win-Rate-Analyzer**)

一个功能强大的交互式Python工具，用于通过OpenDota API分析Dota 2比赛数据，计算在率先达到指定经济领先后，对最终胜率的影响，并生成可视化图表。

## ✨ 功能特性

- **交互式命令行界面**：无需修改代码，通过问答方式轻松设置所有分析参数。
- **两种分析模式**：
  - **抽样调查模式**：分析与您水平相近的玩家群体，获得更具普遍性的统计结果。
  - **个人战绩模式**：深度分析您自己的近期比赛，了解自身表现。
- **智能数据获取**：内置自动请求解析和智能重试机制，最大限度提高数据获取成功率。
- **深度数据洞察**：自动计算“领先后胜率”和“翻盘成功率”等关键指标。
- **自动化报告与可视化**：
  - 生成包含详细数据和统计概要的Excel报告。
  - 自动绘制按段位分析的胜率柱状图和胜负分布饼状图。

## ⚙️ 安装与环境准备

1.  确保您已安装 Python 3.8 或更高版本。
2.  克隆或下载本仓库代码到您的本地。
3.  进入项目文件夹，通过命令行安装所有必需的Python库：
    ```bash
    pip install -r requirements.txt
    ```

## 🚀 如何使用

1.  在项目文件夹中打开您的终端或命令提示符。
2.  运行主脚本：
    ```bash
    python dota_analyzer_interactive.py
    ```
3.  根据屏幕上的提示，依次输入您的选择和参数（例如：分析模式、您的Account ID、比赛数量、经济领先阈值等）。
4.  Account ID 在: https://www.dotabuff.com 搜索自己的DOTA ID 然后 网页栏中最后便是
5.  程序将自动开始执行。如果选择“抽样调查模式”，请耐心等待所有流程完成。
6.  分析结束后，您会在项目文件夹下找到：
    - 一个名为 `dota_analysis_report_... .xlsx` 的Excel报告文件。
    - 一个名为 `plots` 的文件夹，其中包含了生成的图表图片。

## 🙏 致谢与署名 (Acknowledgments)

这个工具的诞生源于一次数据分析的探索，其核心逻辑和功能是在与Google的AI模型 **Gemini** 的深度协作与反复迭代中共同开发的。Gemini在整个过程中提供了代码编写、逻辑优化、错误排查和功能完善等关键帮助。

This tool was born from an exploration into data analysis. Its core logic and features were co-developed in a deep and iterative collaboration with Google's AI model, **Gemini**. Gemini provided critical assistance throughout the process, including code generation, logic optimization, debugging, and feature enhancement.

## 📄 许可证 (License)


本 sourdough 项目基于 [MIT License](LICENSE) 开源。
