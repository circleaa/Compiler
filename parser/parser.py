import os
from collections import defaultdict

EPSILON = "ε" # 用於 first 集合計算

#-------------------------讀取 Grammar----------------------
# 處理production右邊的字串
def tokenize_rhs(rhs_str, terminals, nonterminals):  
    s = rhs_str.strip()  # 去掉兩邊空白
    if s == "" or s == EPSILON:  # 空字串
        return []

    tokens = []
    i = 0   # 目前掃描位置
    L = len(s)

    symbols = nonterminals + terminals # 建立symbols列表
    symbols = sorted(symbols, key=lambda x: -len(x)) # symbols長度降序排序(優先匹配"id"而不是"i")

    while i < L: # 遍歷整個輸入字串
        matched = False
        for sym in symbols: # 按照排序順序遍歷所有symbols
            if s.startswith(sym, i): # 檢查s是否以sym開頭
                tokens.append(sym) # 將sym加到tokens列表
                i += len(sym)
                matched = True
                break
        if matched:
            continue

        raise ValueError(f"Cannot tokenize RHS near: '{s[i:]}' inside '{rhs_str}'")
    return tokens

def load_grammar(grammar_file):
    terminals = []
    nonterminals = []
    productions = defaultdict(list)
    prod_order = [] # 完整 production 順序

    # if l.strip()：忽略空行 / strip()：去掉前後空白
    with open(grammar_file, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]

    terminals = [t.strip() for t in lines[0].split(":")[1].split(",")] # terminal: a, b
    nonterminals = [nt.strip() for nt in lines[1].split(":")[1].split(",")] # nonterminal: S, A

    if "$" not in terminals: # 確保terminals列表中包含結束符號 $\$$
        terminals.append("$")

    for line in lines[2:]: # 從第3行開始文法 A->aA|b
        head, rhs = line.split("->")
        head = head.strip() # A
        alts = [alt.strip() for alt in rhs.split("|")] # aA、b

        for alt in alts: # 把 alts 切成字元
            toks = tokenize_rhs(alt, terminals, nonterminals)
            toks_tuple = tuple(toks)
            productions[head].append(toks_tuple) # 將規則加到 productions 字典中
            prod_order.append((head, toks_tuple)) # 存原始讀取順序

    return terminals, nonterminals, productions, prod_order

#-------------------------- FIRST sets ------------------------
def compute_first_sets(terminals, nonterminals, productions): # 計算單個符號的FIRST
    FIRST = {}
    all_symbols = set(terminals) | set(nonterminals) | set(productions.keys())
    # 初始化(若是terminals->FIRST(s) = {s} / 若是nonterminals->先設為空集合)
    for s in all_symbols: 
        FIRST[s] = {s} if s in terminals else set()
            
    changed = True
    while changed: # 若無更新就結束
        changed = False
        for head in productions.keys(): # 遍歷每個nonterminal
            for body in productions[head]: # 右邊的符號序列
                can_derive_epsilon = True # 假設當前 body 可以推導出 ε
                for symbol in body:  # 遍歷 body 中的每一個符號
                    # 若symbol是terminal(a)->FIRST(a)就是{a} / 若是nonterminal(B)->先看目前FIRST(B)的值
                    symbol_first = FIRST.get(symbol, {symbol} if symbol in terminals else set())
                    
                    # 將此符號的FIRST集合加入到當前head的FIRST集合中（去掉 ε）
                    new_symbols = symbol_first - {EPSILON}
                    if not new_symbols.issubset(FIRST[head]):
                         FIRST[head].update(new_symbols)
                         changed = True
                    
                    # 若此符號的FIRST不包含ε，表示head -> body不能推導出ε
                    if EPSILON not in symbol_first:
                        can_derive_epsilon = False # 中斷對body剩下符號的遍歷
                        break 

                # 若所有符號的FIRST都包含ε -> head的FIRST也要加入ε
                if can_derive_epsilon:
                    if EPSILON not in FIRST[head]:
                        FIRST[head].add(EPSILON)
                        changed = True
                        
    return FIRST

def first_of_string(symbols, FIRST, terminals): # 計算一串符號的FIRST集合
    result = set()
    if not symbols: # 若為空字串->FIRST(ε)={ε}
        return {EPSILON}

    for s in symbols:
        s_first = FIRST.get(s, {s} if s in terminals else set())
        
        if s in terminals: # s是terminals
            result.add(s)
            return result
        
        result.update(s_first - {EPSILON})

        if EPSILON not in s_first: # s不能導出ε
            return result

    result.add(EPSILON) # 每個符號都能導出 ε
    return result

#-------------------------LR(1) Closure------------------------
def closure(items, productions, FIRST, terminals):
    # items : (head, body, dot, lookahead->接下來可能的輸入符號)
    closure_map = defaultdict(set) 
    for (h, b, d, la) in items: # key = (head, body, dot)
        closure_map[(h, b, d)].add(la) # 將相同key的lookahead合併

    changed = True
    while changed:
        changed = False
        for (head, body, dot), lookaheads in list(closure_map.items()):
            if dot >= len(body): # 點已經到達production最後->跳過
                continue

            B = body[dot] # 當前指向的符號（下一個要匹配的符號）
            beta = body[dot+1:] # 之後的符號序列

            if B not in productions: # B為terminal或是無對應production->跳過
                continue

            for la in list(lookaheads): # 遍歷當前key的每個lookahead
                first_set = first_of_string(beta + (la,), FIRST, terminals)
                valid_lookaheads = first_set - {EPSILON} # ε只用來判斷推導，不是lookahead
				# 對B的每個production建立一個新的LR(1)項目核心
                for prod in productions[B]: 
                    key = (B, prod, 0)
                    # 計算新加入的 lookahead
                    new_lookaheads_for_key = valid_lookaheads - closure_map[key]
                    if new_lookaheads_for_key:
                        closure_map[key].update(new_lookaheads_for_key)
                        changed = True

	# 將 closure_map 展開成標準的 LR(1) 項目集合
    result = set()
    for (h, b, d), las in closure_map.items():
        for la in las:
            result.add((h, b, d, la))

    return result

#--------------------------Goto---------------------------
def goto(items, symbol, productions, FIRST, terminals):
    moved = set() # 存所有點號移動後的項目
    for (head, body, dot, la) in items: # 點號後面的符號是否是當前讀入的symbol
        if dot < len(body) and body[dot] == symbol:
            moved.add((head, body, dot+1, la)) # 點號向右移動一位
    return closure(moved, productions, FIRST, terminals) # 算點號移動後的closure

#--------------------LR(1) Canonical Collection---------------------------
def build_lr1_automaton(start_symbol, terminals, nonterminals, productions):
    FIRST = compute_first_sets(terminals, nonterminals, productions)
    start_item = (start_symbol, productions[start_symbol][0], 0, "$")

    C = []
    initial_set = closure({start_item}, productions, FIRST, terminals) # I0狀態
    C.append(initial_set) # 將I0加入狀態集合C中
    transitions = {} # 存GOTO轉換結果
	
	# 確定GOTO符號順序
    nt_order = ([start_symbol] + [nt for nt in nonterminals 
                                  if nt != start_symbol]) # 放nonterminals的順序(按列表順序)
    t_order = sorted(t for t in terminals if t != "$") # 放terminals的順序(按字母序排序)
    if "$" in terminals:
        t_order.append("$")	# 把 $ 放到所有終結符的最後
    goto_symbols = nt_order + t_order
       
    done = False   
    while not done:
        done = True
        for i, I in enumerate(list(C)): # 遍歷當前所有的狀態Ii
            for X in goto_symbols:
                # 計算從狀態I讀入符號X所到達的新項目集J
                goto_I_X = goto(I, X, productions, FIRST, terminals)
                if goto_I_X:
                    found = False
                    for j, existing in enumerate(C): # 檢查重複
                        if goto_I_X == existing: # 狀態相等判斷
                            # 找到相同的狀態Ij，則記錄狀態轉移：從i讀入X轉移到j
                            transitions[(i, X)] = j
                            found = True
                            break
                    if not found: # 是新狀態，將其添加到C的末尾
                        C.append(goto_I_X)
                        # 記錄轉移：從i讀入X轉移到這個新的狀態
                        transitions[(i, X)] = len(C) - 1
                        done = False
    
    return C, transitions

#--------------------------格式化印出 Item -------------------
def merge_items(items, augmented_start, prod_index):
    merged = {}
    for (head, prod, dot, la) in items: # 遍歷輸入的每個LR(1)項目
        key = (head, tuple(prod), dot)
        merged.setdefault(key, set()).add(la) # 若key已經存在->合併lookahead

    def sort_key(key): # 對合併後的項目核心進行排序
        head, prod, dot = key
        
        if head == augmented_start: # S'永遠最優先(-1)
            return (-1, 0, dot)
        
        prod_order = prod_index.get((head, prod), 10**9)
        return (0, prod_order, dot) # 依 production 輸入順序

    result = []
    for key in sorted(merged.keys(), key=sort_key):
        head, prod, dot = key
        las = sorted(merged[key]) # 對lookahead進行字母排序
		# 格式化輸出字串
        left = "".join(prod[:dot])
        right = "".join(prod[dot:])
        dotted = left + "." + right

        result.append([f"{head}->{dotted}", las])
        
    return result

#------------------輸出所有 productions(第一行)----------------------
def print_all_productions(prod_list, start_symbol):
    prods = []
    prods.append(f"{start_symbol}'->.{start_symbol}")
    for head, body in prod_list: # 按照順序
        prods.append(f"{head}->" + "".join(body))
    print(prods)

#---------------- print_states (調用 merge_items)---------------------
def print_states(C, augmented_start, prod_index):
    print_all_productions(prod_list, actual_start_symbol) # 列reduce規則
    print("//////////////////// state ////////////////////")
    for idx, I in enumerate(C): # 遍歷每個狀態I
        display = merge_items(I, augmented_start, prod_index)
        print(f"{idx} : {display}")

#---------------------為grammar建立順序編號-------------------------
def build_prod_list_and_map(prod_order):
    prod_list = []
    prod_to_num = {}

    for idx, prod in enumerate(prod_order):
        prod_list.append(prod) # 按r編號順序排列的規則列表
        prod_to_num[prod] = idx + 1  # 規則到編號的字典

    return prod_list, prod_to_num

#-------------------建構 Parsing Table (LR(1))-----------------
def build_parsing_table(C, transitions, productions,
                        terminals, nonterminals,
                        prod_to_num,
                        start_symbol):

    start_symbol_aug = start_symbol + "'" # S'、E'...
    ACTION = {i: {} for i in range(len(C))}
    GOTO   = {i: {} for i in range(len(C))}

    for i, I in enumerate(C): # 遍歷每個LR(1)狀態I
        for (head, body, dot, la) in I:
            # ---------------- SHIFT ----------------
            if dot < len(body): # 點號不在最右側
                symbol = body[dot] # 點號後的符號
                if symbol in terminals:
                    if (i, symbol) in transitions: # 檢查transitions表中的轉移記錄
                        # 填shift + 轉移到的狀態編號
                        ACTION[i][symbol] = f"s{transitions[(i, symbol)]}"

            # ------------ REDUCE / ACCEPT ----------
            else: # 點號在最右側
                if (head == start_symbol_aug and body == (start_symbol,) 
                    and la == "$"): # Accept
                    ACTION[i]["$"] = "Acc"
                    continue

                rnum = prod_to_num.get((head, body)) # 取當前規則的r編號
                if rnum is None:
                    raise ValueError(
                        f"Production {(head,body)} not found in prod list mapping."
                    )
                ACTION[i][la] = f"r{rnum}" # 填reduce + r編號

        # ---------------- GOTO ----------------
        for nt in nonterminals: # 遍歷nonterminals
            if (i, nt) in transitions: # 檢查transitions表中是否存在GOTO(I,A)的轉移記錄
                GOTO[i][nt] = transitions[(i, nt)] # 在表中填入轉移到的狀態編號

    return ACTION, GOTO

#--------------------------印出 Parsing Table---------------------------
def print_parsing_table(ACTION, GOTO, terminals, nonterminals):
    print("//////////////////// parsing table ////////////////////")
    header = [" ", *terminals, *nonterminals] # 表格的列順序
    col_widths = [max(3, len(h)) for h in header]

    # 用於列印表格的頂部、底部和分隔線
    def border():
        print("+" + "+".join("-" * w for w in col_widths) + "+")
    border()
    print("|" + "|".join(h.center(w) for h, w in zip(header, col_widths)) + "|")
    border()

    for state in sorted(ACTION.keys()):
        row = [str(state)]
        for t in terminals: # ACTION欄位
            row.append(ACTION[state].get(t, ""))
        for nt in nonterminals: # GOTO欄位
            row.append(str(GOTO[state].get(nt, "")))

        print("|" + "|".join(s.center(w) for s, w in zip(row, col_widths)) + "|")
    border()

#--------------------------Parsing 過程-------------------------------
def tokenize_input(s, terminals):
    tokens = []
    i = 0
    L = len(s)
    
    # terminals 長度由長到短排序，避免 id 被誤拆成 i+d
    sorted_terms = sorted(terminals, key=lambda x: -len(x))
    
    while i < L:
        matched = False
        for term in sorted_terms: # 長度由長到短遍歷terminal
            if term == "$":
                continue  # 忽略 $，它只用於end
            if s.startswith(term, i): # 檢查s從當前位置i開始是否以term開頭
                tokens.append(term) # terminal加入Tokens列表
                i += len(term)
                matched = True
                break
        if matched:
            continue
        
        if s[i].isspace(): # 忽略空白
            i += 1
            continue
        # 無法匹配任何 terminal -> invalid
        raise ValueError(f"Invalid character(s) in input at position {i}: '{s[i:]}'")
    return tokens

def parse_string(s, ACTION, GOTO, prod_list, productions, terminals, augmented_start):
    try: # 對輸入字串進行詞法分析
        symbols = tokenize_input(s, terminals) + ["$"]
    except ValueError as e:
        print(f"parsing: {s}")
        print("Invalid character exist!")
        print("result: Invalid!")
        return False

    print(f"parsing: {s}")
    stack = [0] # 初始狀態I0開始
    ip = 0 # 指向當前讀取的輸入Token

    print("+-------+----------------+--------+")
    print("| stack | input          | action |")
    print("+-------+----------------+--------+")

    def stack_str(): # 內容格式化
        return "".join(str(x) for x in stack)

    while True: # 只要還未Accept或遇到錯誤，就持續循環
        state = stack[-1]
        a = symbols[ip]
        # 查閱ACTION[i,a]，如果查不到，則錯誤
        action = ACTION[state].get(a, "X")

        print("| " + stack_str().ljust(6) + " | " +
              "".join(symbols[ip:]).ljust(14) + " | " + action.center(6) + " |")

        if action == "X": # 錯誤
            print("+-------+----------------+--------+")
            print("result: Invalid!")
            return False
		# Shift
        if action.startswith("s"): 
            next_state = int(action[1:]) # 提取目標狀態
            stack.append(a) # 將當前輸入符號a放入stack
            stack.append(next_state) # 將目標狀態放入stack
            ip += 1 # 讀取下一個輸入符號
		# Reduce
        elif action.startswith("r"): 
            r = int(action[1:]) # 提取規則編號
            head, body = prod_list[r-1] # 根據編號查找對應規則
            for _ in range(len(body)*2): # 計算pop次數
                stack.pop()
            state2 = stack[-1] # 獲取stack top狀態
            if head == augmented_start: # Accept
                print("+-------+----------------+--------+")
                print("result: Valid!")
                return True
            stack.append(head) # 將reduce後的nonterminal A放入stack
            stack.append(GOTO[state2][head]) # 查GOTO將查到的新狀態放入stack

        elif action == "Acc":
            print("+-------+----------------+--------+")
            print("result: Valid!")
            return True

#---------------------------MAIN------------------------------
if __name__ == "__main__":
    input_root = "input" # 測資放在input/資料夾下

    if not os.path.exists(input_root): # input/ 不存在
        print(f"Error: Input directory '{input_root}' not found. Please create it.")
        exit()

    for folder in sorted(os.listdir(input_root)):  # 遍歷所有測資資料夾
        folder_path = os.path.join(input_root, folder)
        if not os.path.isdir(folder_path):
            continue

        grammar_path = os.path.join(folder_path, f"{folder}_grammar.txt")
        testdata_path = os.path.join(folder_path, f"{folder}_testdata.txt")

        if not (os.path.exists(grammar_path) and os.path.exists(testdata_path)):
            continue # 測資資料夾缺檔案->跳過

        print("=======================================")
        print(f"Processing Test Case: {folder}")
        print(f"Grammar: {grammar_path}")
        print(f"Testdata: {testdata_path}")
        print("=======================================\n")

        # 呼叫 load_grammar 讀取 grammar_txt
        terminals, nonterminals, productions, prod_order = load_grammar(grammar_path)
        if not nonterminals: # 若無nonterminals->跳過
            print("Error: Grammar file contains no nonterminals.")
            continue
            
        # 把第一個nonterminal設為起始符號(S、E...)
        actual_start_symbol = nonterminals[0]
        
        # 建立augmented_start(S'、E'...)
        augmented_start = actual_start_symbol + "'"
        productions[augmented_start] = [(actual_start_symbol,)]
		
        # 按照輸入順序對productions編號(reduce時需要)
        prod_list, prod_to_num = build_prod_list_and_map(prod_order)
		
        prod_index = {} # 建立 production -> index 的對照表(輸出items時的順序)
        for i, (h, b) in enumerate(prod_order):
            prod_index[(h, b)] = i
		
        # C：Canonical LR(1) item sets（states）/ transitions：DFA 邊（goto）
        C, transitions = build_lr1_automaton(augmented_start, terminals, nonterminals, productions)
        print_states(C, augmented_start, prod_index) # 印出每個 state 的 LR(1) items
        
        ACTION, GOTO = build_parsing_table(C, transitions, productions, terminals, nonterminals, prod_to_num, actual_start_symbol)
        print_parsing_table(ACTION, GOTO, terminals, nonterminals)

        # 讀取 testdate_txt
        with open(testdata_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]

        for s in lines: # 進行 LR parsing
            parse_string(s, ACTION, GOTO, prod_list, productions, terminals, augmented_start)