# LR(1) Syntax Parser (語法分析器)

![C++](https://img.shields.io/badge/C++-00599C?style=flat-square&logo=c%2B%2B)
![Automata Theory](https://img.shields.io/badge/Theory-Automata-B22222?style=flat-square)
![Compiler Design](https://img.shields.io/badge/Domain-Compiler_Design-4B0082?style=flat-square)

## Introduction
本專案為編譯器前端 (Compiler Front-end) 之核心實作。系統能動態讀取 Context-Free Grammar (CFG)，自動推導並建構 LR(1) 狀態機 (State Machine)，最終生成具備 Lookahead 能力的 Parsing Table (Action & Goto 表)。

系統能利用生成的分析表，精準模擬編譯器底層的 Shift 與 Reduce 堆疊操作，判斷輸入之測資字串是否符合定義之語法規範。

[完整題目](./1141_compiler.pdf)

## Demo
系統會詳細印出狀態機生成結果、Parsing Table，以及每一筆測試字串的推導過程。

```text
// 語法分析推導過程 (Stack Simulation)
parsing: bb
result: Valid!
| stack    | input | action |
| 0        | bb$   | s4     |
| 0b4      | b$    | r3     |
| 0A2      | b$    | s7     |
| 0A2b7    | $     | r3     |
| 0A2A5    | $     | r1     |
| 0S1      | $     | Acc    |
```

## Algorithm Pipeline
系統開發邏輯嚴格遵循編譯器設計理論，主要分為三個模組：

1. **語法前處理 (Grammar Parsing)：**
   解析 `terminal` 與 `nonterminal` 集合，並讀取 Production Rules 建立 CFG 內部資料結構[cite: 6]。
2. **LR(1) 狀態機建構 (State Machine Generation)：**
   實作 `Closure()` 與 `GoTo()` 演算法。透過計算 First Set 處理 Lookahead 標記，動態展開所有可能的語法狀態 (States)，避免 Shift/Reduce 衝突[cite: 6]。
3. **語法分析與驗證 (Parsing & Validation)：**
   建構 Action/Goto Table 後，透過 Stack 資料結構模擬語法分析過程。系統能即時輸出當前 Stack 狀態、剩餘 Input 以及對應的 Action (Shift/Reduce/Accept)[cite: 6]。

## Error Handling
系統具備嚴格的語法檢驗機制：
*   **Invalid Character Rejection：** 若輸入字串包含未定義於 `terminal` 列表之字元（如輸入 `aca` 但 `c` 未定義），系統會立即中斷並拋出 `Invalid character exist!` 錯誤。
*   **Syntax Error Detection：** 遇無法匹配 Parsing Table 的非法語法結構時，精準判定為 `Invalid!`。
