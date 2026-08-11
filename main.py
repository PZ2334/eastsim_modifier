import binascii
import os
import struct  # 引入struct模块用于处理浮点数和字节的转换
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import simpledialog

def float_to_little_endian_hex(float_value):
    """
    将一个浮点数转换为小端序的十六进制字符串。
    例如: 10.0 -> '00002041'
    """
    try:
        # '<f' 表示小端序 (little-endian) 的单精度浮点数 (4字节)
        packed_bytes = struct.pack('<f', float_value)
        # .hex() 将字节转换为十六进制字符串
        return packed_bytes.hex()
    except (struct.error, TypeError) as e:
        print(f"浮点数转换错误: {e}")
        return None

def modify_file(file_path, user_float_str, index_n):
    """
    根据用户输入的浮点数、整数n和预设规则修改文件。
    规则:
    1. 搜索第 (n+1) 个 "FF FF FF FF" 块。
    2. 从该块向后搜索 "proctep" 标记 (70726f6373746570)。
    3. 如果找不到 proctep，报错。
    4. 如果找到了，检查 "FFFFFFFF" 后面的数据：
       - 如果后面是 "00 00 00 00"，则插入固定数据 + 用户浮点数HEX
       - 如果后面是固定数据 "12000000b2bdd6e8bde1caf83a20b2d9d7f7d5fdc8b701000000"，
         则在该固定数据后面（偏移32字节处）替换为用户浮点数HEX
       - 其他情况报错。
    """
    # --- 1. 验证并转换用户输入 ---
    try:
        user_float = float(user_float_str)
    except ValueError:
        messagebox.showerror("输入错误", f"无法将 '{user_float_str}' 转换为有效的浮点数。")
        return

    float_hex = float_to_little_endian_hex(user_float)
    if float_hex is None:
        messagebox.showerror("转换错误", "浮点数到HEX的转换失败。")
        return

    # --- 常量定义 ---
    FF_BLOCK_HEX = "ffffffff"
    PROCTEP_HEX = "70726f6373746570"  # "proctep"
    # 固定数据（32字节 = 64个HEX字符）
    FIXED_DATA_HEX = "12000000b2bdd6e8bde1caf83a20b2d9d7f7d5fdc8b701000000"
    
    print(f"用户输入: {user_float}, 转换后的HEX: {float_hex}")
    print(f"将在第 {index_n + 1} 个 'FFFFFFFF' 块中进行操作")

    # --- 2. 读取文件 ---
    try:
        with open(file_path, 'rb') as f:
            original_data = f.read()
    except FileNotFoundError:
        messagebox.showerror("错误", f"文件未找到: {file_path}")
        return
    except Exception as e:
        messagebox.showerror("错误", f"读取文件时发生错误: {e}")
        return

    # --- 3. 查找并修改 ---
    hex_str = original_data.hex()
    
    # 查找所有 "FFFFFFFF" 块的起始位置
    ff_block_positions = []
    search_start = 0
    while True:
        pos = hex_str.find(FF_BLOCK_HEX, search_start)
        if pos == -1:
            break
        ff_block_positions.append(pos)
        search_start = pos + 1

    # 检查 n 是否有效
    if index_n < 0 or index_n >= len(ff_block_positions):
        messagebox.showerror("输入错误", f"输入的整数 n={index_n} 无效。\n文件中只找到了 {len(ff_block_positions)} 个 'FFFFFFFF' 块 (索引从0到{len(ff_block_positions)-1})。")
        return

    # 获取第 n+1 个块的起始位置
    target_ff_pos = ff_block_positions[index_n]
    print(f"第 {index_n + 1} 个 'FFFFFFFF' 块的起始位置 (HEX索引): {target_ff_pos}")

    # 从该块开始，向后查找 "proctep"
    proctep_pos = hex_str.find(PROCTEP_HEX, target_ff_pos)
    if proctep_pos == -1:
        messagebox.showerror("错误", f"在第 {index_n + 1} 个 'FFFFFFFF' 块之后未找到 'proctep' 标记。")
        return
    
    print(f"'proctep' 标记的起始位置 (HEX索引): {proctep_pos}")

    # 检查 "FFFFFFFF" 后面的数据
    # "FFFFFFFF" 本身是8个HEX字符（4字节）
    data_after_ff_pos = target_ff_pos + len(FF_BLOCK_HEX)
    
    # 读取后面4个字节（8个HEX字符）来判断
    if data_after_ff_pos + 8 > len(hex_str):
        messagebox.showerror("错误", "文件数据不足，无法读取 'FFFFFFFF' 后面的数据。")
        return
    
    next_4bytes_hex = hex_str[data_after_ff_pos:data_after_ff_pos + 8]
    print(f"'FFFFFFFF' 后面的4字节: {next_4bytes_hex}")

    modified_hex_str = hex_str
    
    # 情况一: 后面是 "00 00 00 00"
    if next_4bytes_hex == "00000000":
        print("检测到 '00000000'，执行插入操作。")
        # 在 "FFFFFFFF" 后面插入固定数据 + 浮点数
        insert_pos = data_after_ff_pos
        data_to_insert = FIXED_DATA_HEX + float_hex
        
        modified_hex_str = (
            hex_str[:insert_pos] +
            data_to_insert +
            hex_str[insert_pos:]
        )
        print(f"在位置 {insert_pos} 插入了 {len(data_to_insert)} 个字符。")

    # 情况二: 后面是固定数据
    elif next_4bytes_hex == "12000000":
        # 检查后面是否完整匹配固定数据（32字节 = 64个HEX字符）
        if data_after_ff_pos + len(FIXED_DATA_HEX) > len(hex_str):
            messagebox.showerror("错误", "文件数据不足，无法完整读取固定数据块。")
            return
        
        following_data = hex_str[data_after_ff_pos:data_after_ff_pos + len(FIXED_DATA_HEX)]
        print(f"'FFFFFFFF' 后面的32字节: {following_data}")
        
        if following_data == FIXED_DATA_HEX:
            print("检测到完整的固定数据块，执行替换操作。")
            # 在固定数据后面（偏移32字节处）替换为用户浮点数
            # 固定数据是32字节，所以修改位置 = data_after_ff_pos + 32*2 (HEX字符)
            modify_pos = data_after_ff_pos + len(FIXED_DATA_HEX)
            
            if modify_pos + 8 > len(hex_str):
                messagebox.showerror("错误", "计算出的修改位置将超出文件末尾。")
                return
            
            # 替换4字节（8个HEX字符）
            modified_hex_str = (
                hex_str[:modify_pos] +
                float_hex +
                hex_str[modify_pos + 8:]
            )
            print(f"在位置 {modify_pos} 处将原有数据覆盖为 {float_hex}。")
        else:
            messagebox.showerror("格式错误", f"'FFFFFFFF' 后面的数据不匹配预期的固定数据块。")
            return

    # 其他情况: 不是 "00000000" 也不是 "12000000"
    else:
        messagebox.showerror("格式错误", f"第 {index_n + 1} 个 'FFFFFFFF' 块后面的数据为 {next_4bytes_hex}，\n不符合预期的 '00000000' 或 '12000000'，无法处理。")
        return

    # --- 4. 保存新文件 ---
    try:
        modified_data = bytes.fromhex(modified_hex_str)
    except ValueError as e:
        messagebox.showerror("错误", f"十六进制转换回二进制失败，修改逻辑可能有误: {e}")
        return

    # 生成新文件名
    base_name, ext = os.path.splitext(file_path)
    output_path = f"{base_name}(已破解){ext}"

    try:
        with open(output_path, 'wb') as f:
            f.write(modified_data)
    except Exception as e:
        messagebox.showerror("错误", f"写入新文件时发生错误: {e}")
        return

    # --- 5. 显示成功信息 ---
    success_message = (
        f"破解完成！\n\n"
        f"文件: {os.path.basename(file_path)}\n"
        f"新文件已保存为: {output_path}"
    )
    messagebox.showinfo("成功", success_message)
    print(f"文件已成功保存为: {output_path}")


def select_file_path():
    """打开文件对话框让用户选择文件"""
    file_path = filedialog.askopenfilename(
        title="请选择要破解的文件",
        filetypes=[("所有文件", "*.*"), ("PF文件", "*.pf")]
    )
    if file_path:
        directory_entry.delete(0, tk.END)
        directory_entry.insert(0, file_path)
        directory_label.config(text=f"已选择文件: {os.path.basename(file_path)}")

def apply_hook():
    """点击'开始破解'按钮时触发的函数"""
    file_path = directory_entry.get()
    user_float_str = float_entry.get()
    n_str = n_entry.get() # 获取 n 的输入

    if not file_path:
        messagebox.showerror("错误", "请先选择一个文件。")
        return
    if not user_float_str:
        messagebox.showerror("错误", "请输入一个十进制浮点数。")
        return
    
    # 验证 n 的输入
    try:
        index_n = int(n_str)
    except ValueError:
        messagebox.showerror("输入错误", f"无法将 '{n_str}' 转换为有效的整数 n。")
        return

    # 调用核心修改函数，并传入 n
    modify_file(file_path, user_float_str, index_n)

# --- GUI 界面设置 ---
root = tk.Tk()
root.title("东方仿真破解工具")

# 设置窗口大小（不可调整）
root.geometry("500x300") # 稍微增加高度以容纳新控件
root.resizable(False, False)

# 创建控件
main_frame = tk.Frame(root, padx=10, pady=10)
main_frame.pack(fill=tk.BOTH, expand=True)

# 文件选择部分
directory_label = tk.Label(main_frame, text="原文件路径（未选择）", wraplength=480)
directory_label.pack(anchor="w", pady=(0, 5))

directory_entry_frame = tk.Frame(main_frame)
directory_entry_frame.pack(fill=tk.X, pady=5)
directory_entry = tk.Entry(directory_entry_frame)
directory_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
browse_button = tk.Button(directory_entry_frame, text="浏览...", command=select_file_path)
browse_button.pack(side=tk.LEFT, padx=(5, 0))

# 浮点数输入部分
float_label = tk.Label(main_frame, text="请输入需要修改的成绩 (例如 10.0):")
float_label.pack(anchor="w", pady=(10, 5))
float_entry = tk.Entry(main_frame)
float_entry.pack(fill=tk.X, pady=5)
float_entry.insert(0, "10.0") # 设置一个默认值

# --- 新增的 n 输入部分 ---
n_label = tk.Label(main_frame, text="请输入可修改的第 n 个步骤（整数，从0开始） :")
n_label.pack(anchor="w", pady=(10, 5))
n_entry = tk.Entry(main_frame)
n_entry.pack(fill=tk.X, pady=5)
n_entry.insert(0, "1") # 默认值为1，对应第2个块

# 按钮部分
apply_button = tk.Button(main_frame, text="开始破解", command=apply_hook, height=2)
apply_button.pack(fill=tk.X, pady=(20, 0))

# 进入主事件循环
root.mainloop()
