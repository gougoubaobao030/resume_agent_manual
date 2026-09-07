from services.resume_service import parse_resume_text


resume_text = """
姓名︓勾勾 | 求职岗位︓U3D初级⼯程师
⾃我介绍
持续学习︓在⼯作后⾃学编程等技能，挖掘技术热情 • 解决问题能⼒︓善于定位问题 
，以编程为例--⾃⼰提炼了学会编程的四⼤法则 • 伴随⽣活阅历，真诚⾄上。       
技术栈
熟悉C#︓OOP、委托、回调、事件、扩展⽅法、异步编程、泛型、LINQ等等 • 熟悉Unity︓3D数学、熟悉⽣命周期函数、协程、物理系统、动画等系统、Addressables异 步资
源加载卸载、熟悉UGUI等等
C++︓了解STL，Qt/SDL2/OpenGL⼩Demo • 数据结构与算法︓截⾄目前LeetCode通过262题，对性能和内存有⼀定感知 • 其他了解︓了解Python/Lua | TCP/IP⽹络协议基本原
理 | MVC架构SOLID原则 | Json序列化 反序列化 | Git/GitHub | Linux基础        
项目经验︓ Unity3D 中型RPG
摘要
通过⼤量AI辅助，资料查阅，从 0 到 1，基于UGUI发开个⼈独⽴中型架构Demo，实践 
了各
⼤模块基础功能，模块化架构，代码解耦，性能优化等内容。
视频链接︓ Demo动画 | 源码:
源码
总览
架构设计︓SO数据驱动，中枢层控制，接⼝抽象，表现层UI逻辑分离，委托事件，事件
总
线, 通⽤⼯具，输⼊抽象，对象池
设计模式应⽤︓⼯⼚、策略、依赖注⼊（DI）、单例、命令、观察者, 状态类等 • 性 
能优化︓全局对象池（技能特效/敌⼈/商品背包UI/⾎条UI等）降低 GC 压⼒︔⽆alloc API 留学⽇本
设计模式应⽤︓⼯⼚、策略、依赖注⼊（DI）、单例、命令、观察者, 状态类等 • 性 
能优化︓全局对象池（技能特效/敌⼈/商品背包UI/⾎条UI等）降低 GC 压⼒︔⽆alloc API 进⾏物理检测︔状态缓存，优化若⼲算法。
防御性编程 ，如条件宏编译，代码结构服务于调试，OnGUI可视化Debug⼯具框架     
以技能系统为例
功能
使⽤范围检测实现多类型技能︓单体 / 远程 / 范围 / 爆炸/ 投掷 /闪现，攻击范围 
Gizmo 可
视化
⼤量使⽤ Physics.OverlapSphereNonAlloc，有效减少 GC Alloc • 协程以及事件驱动
下的公共 CD（GCD）+ 单体 CD 的双冷却体系 • UI事件监听下的实现拖拽调整技能栏 
随意调整按键位置
代码设计
接⼝驱动︓泛型基类构建，通过 ISkill 接⼝ + SkillBase 抽象类分离职责⼯⼚模式 
⽣成 • 输⼊抽象︓分离 InputProvider，⽀持未来灵活切换键盘 / ⼿柄 / AI 输⼊ • 系统联动︓SkillBar → SkillExecutor → UI_SkillBar 串联，实现 UI 与技能逻辑同
步
基本信息
gougoubaobao030@gmail.com
450777820@qq.com
+86-139-5824-8237
1992-05-31（33）
性别︓ ⼥
学历资格相关
▼ 学历
2010/09 - 2014/06
宁波⼤学（双⼀流）
阳明班(特优班)特别荣誉
会计学学⼠学位
2024/09-2025/10
▼ 证书
英语四级(2012)
⽇语N1证书(2017/12)
商务⽇语结业证书(2025/06)
注︓
计算机学习多⽤英语资料
▼ 为什么留学？
开阔视野和各国⼈⼠学习游戏开发 • 参加多个东京游戏展会活动 • 了解⽇本游戏市场
其他各⼤模块摘要
敵AI
结合动画事件与 CharacterController，动画帧攻击判定，不同模型相同骨骼 • 3d数 
学点乘，叉乘, 四元数下的玩家位置追踪检测，扇形等伤害范围计算 • 结合 NavMeshAgent、NavMeshObstacle，动态障碍更新， AI 寻路 • Facade 架构︓基于 EnemyStateMachine + EnemyDuckStateBase 代码状态机统⼀管理, SkillManager 进⾏时序调度，
地⾯连招等通⽤状态抽象，通过 IAttackable 接⼝接⼊玩家技
交互系统
IInteractable+Command模式，Register即可接⼊︔Mediator协调UI与逻辑︔状态缓存 
优
化︔与主角状态机整合
主角状态机
角⾊控制器/Animator，⼯⼚模式注册新状态，实现地⾯ / 空中策略分离、空中惯性控
制、
跳跃惯性, 随交互系统命令进⼊交互状态禁⽤移动、攻击
商店/背包/物品/对话/任务/采集/⾦币 & UGui
运⽤到UGUI⾥的Scrollview, SliderBar，GridLayout, TMP, UI事件监听, DoTween 动
画等等 • UIManager单例模式统⼀管理, “中控 + 组件”模式，通过事件回调进⾏通信 
• 各模块抽象接⼝，由 GameManager 进⾏依赖注⼊管理︔IReceiver依赖倒置, 事件驱
动, 数 据驱动, 观察者模式, 各模块松耦合协作
对象池
⽣命周期管理︓通过委托回调实现⾃动回收，设置数量上限并有预热机制
DevTool
模块化⼯具框架︓制作 DevToolBox，通过 IDevToolModule 注册统⼀管理 OnGUI / Gizmos • 调试⼯具︓已实现射线坡度检测、交互状态监控、敌⼈ AI 状态可视化、Blink 技能调试等
其他3D经营/射击/物理/2D横板RPG游戏以及练习题实践
⾳效/环境光/主角刚体+KINEMEITC/物理材质/场景转换等Unity基础内容 • Json序列化
反序列化存档/Addressables异步资源加载卸载 • C++源码︓C++/Sdl2射击游戏 | C++/OpenGL | C++/Qt解谜
⼯作经历
2022- 2023 | 个⼈开发⼯作室
开发阳明⼼学⼈员管理系统 • C#/Winform/.Net /C++ /Qt emit/
slot
实现登录系统，CRUD，权限管理 • MVC架构, 设计模式，了解SOLID 原则
实现登录系统，CRUD，权限管理 • MVC架构, 设计模式，了解SOLID 原则
实现Socket⽹络通信，数据建模，
序列化
ORM对接数据库, 数据库设计
2014 - 2021 | 会计/商务相关⼯作
锻炼积累沟通交流能⼒ • 培养了巨⼤的同理⼼ • 积累出从对⽅的角度，第三⽅角度  
看问题的能⼒
简短求职信
与其说是求职，
更希望参与⼀次认真做事的过程，
且⼀直⾃信会越做越好，
越做越精。
若有机会，
我将真诚的以创业者式的责任感参与，
投⼊持续的稳定性。
※ 本简历以 Markdown 构建，基于 HTML/
CSS(VSCode) 真⼼呈现。
"""

candidate = parse_resume_text(
    raw_text=resume_text,
    source_file="manual_test.txt",
)

print(
    candidate.model_dump_json(
        indent=2
    )
)