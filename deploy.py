#!/usr/bin/env python3
import subprocess
import sys
import time
import threading
import os
# python3 /root/WeddingInvitation.com/deploy.py

# --- MÀU SẮC ANSI GIAO DIỆN ---
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# --- ANIMATION SPINNER ---
class Spinner:
    busy = False
    delay = 0.1
    
    @staticmethod
    def spinning_cursor():
        while True: 
            for cursor in '|/-\\': yield cursor
            
    def __init__(self, delay=None):
        self.spinner_generator = self.spinning_cursor()
        if delay and float(delay): self.delay = delay
        
    def spinner_task(self):
        while self.busy:
            sys.stdout.write(next(self.spinner_generator))
            sys.stdout.flush()
            time.sleep(self.delay)
            sys.stdout.write('\b')
            sys.stdout.flush()
            
    def __enter__(self):
        self.busy = True
        threading.Thread(target=self.spinner_task).start()
        
    def __exit__(self, exception, value, tb):
        self.busy = False
        time.sleep(self.delay)
        if exception is not None:
            return False

# --- HÀM TIỆN ÍCH ---
def run_cmd(cmd):
    """Chạy lệnh shell và trả về mã lỗi, stdout, stderr"""
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()
    return process.returncode, stdout, stderr

def log_info(msg):
    print(f"{Colors.CYAN}[*]{Colors.ENDC} {msg}")

def log_success(msg):
    print(f"{Colors.GREEN}[+]{Colors.ENDC} {msg}")

def log_error(msg):
    print(f"{Colors.FAIL}[-]{Colors.ENDC} {msg}")

def log_warning(msg):
    print(f"{Colors.WARNING}[!]{Colors.ENDC} {msg}")

def get_current_branch():
    code, out, err = run_cmd("git rev-parse --abbrev-ref HEAD")
    if code == 0:
        return out.strip()
    return "main"

# --- LOGIC DEPLOY CHÍNH ---
def deploy():
    os.system('clear')
    print(f"{Colors.HEADER}{Colors.BOLD}")
    print("========================================================")
    print(" 🚀 SMART AUTO-DEPLOY SCRIPT - WEDDING INVITATION")
    print("========================================================")
    print(f"{Colors.ENDC}")

    repo_url = "git@github.com:d4m-dev/WeddingInvitation.com.git"
    
    # 1. Kiểm tra Git Init
    if not os.path.exists(".git"):
        log_info("Khởi tạo kho lưu trữ Git...")
        run_cmd("git init")
        log_success("Git đã được khởi tạo.")
        
    # 2. Cấu hình Remote
    log_info("Đang cấu hình remote repository...")
    code, out, err = run_cmd("git remote -v")
    if "origin" not in out:
        run_cmd(f"git remote add origin {repo_url}")
    else:
        run_cmd(f"git remote set-url origin {repo_url}")
    log_success(f"Remote đã được cấu hình: {Colors.CYAN}{repo_url}{Colors.ENDC}")

    # Lấy nhánh hiện tại
    branch = get_current_branch()
    if branch == "HEAD":
        branch = "main"
        run_cmd("git checkout -b main")

    log_info(f"Nhánh hiện tại: {Colors.BOLD}{branch}{Colors.ENDC}")

    # 3. Add & Commit
    sys.stdout.write(f"{Colors.CYAN}[*]{Colors.ENDC} Đang đưa file vào stage và tạo commit... ")
    sys.stdout.flush()
    with Spinner():
        run_cmd("git add .")
        commit_msg = "Auto deploy: " + time.strftime("%Y-%m-%d %H:%M:%S")
        run_cmd(f'git commit -m "{commit_msg}"')
    print(f"{Colors.GREEN}Xong!{Colors.ENDC}")

    # 4. Vòng Lặp Push Thông Minh
    max_attempts = 4
    attempt = 1
    success = False
    force_pushed = False

    while attempt <= max_attempts and not success:
        log_info(f"Đang đẩy code lên GitHub (Thử lần {attempt}/{max_attempts})...")
        
        sys.stdout.write(f"    Pushing... ")
        sys.stdout.flush()
        
        with Spinner():
            push_cmd = f"git push origin {branch}"
            if force_pushed:
                push_cmd = f"git push origin {branch} --force"
            code, out, err = run_cmd(push_cmd)
        
        if code == 0:
            print(f"{Colors.GREEN}Thành công!{Colors.ENDC}")
            success = True
            break
        
        print(f"{Colors.FAIL}Thất bại!{Colors.ENDC}")
        error_output = err.lower()
        
        # --- PHÂN TÍCH LỖI VÀ TỰ ĐỘNG SỬA ---
        if "set-upstream" in error_output or "no upstream branch" in error_output:
            log_warning("Chưa có nhánh upstream. Đang tự động thiết lập upstream...")
            run_cmd(f"git push --set-upstream origin {branch}")
            # Thường thì lệnh trên sẽ tự đẩy code luôn
            success = True
            
        elif "fetch first" in error_output or "non-fast-forward" in error_output:
            log_warning("Remote có code mới hơn. Đang tự động Pull (Rebase)...")
            sys.stdout.write(f"    Pulling... ")
            sys.stdout.flush()
            with Spinner():
                pull_code, pull_out, pull_err = run_cmd(f"git pull origin {branch} --rebase")
            
            if pull_code != 0:
                print(f"{Colors.FAIL}Thất bại!{Colors.ENDC}")
                if "unrelated histories" in pull_err.lower():
                    log_warning("Lịch sử commit không liên quan. Đang tự động merge...")
                    run_cmd(f"git pull origin {branch} --allow-unrelated-histories --no-edit")
                elif "conflict" in pull_err.lower():
                    log_error("Xảy ra xung đột mã (Merge Conflict)!")
                    log_warning("Hủy Rebase và sử dụng Force Push để ưu tiên mã local...")
                    run_cmd("git rebase --abort")
                    force_pushed = True
                else:
                    force_pushed = True
            else:
                print(f"{Colors.GREEN}Xong!{Colors.ENDC}")
                
        elif "permission denied" in error_output or "could not read from remote" in error_output:
            log_error("Từ chối quyền truy cập SSH (Permission Denied)!")
            log_info("Vui lòng kiểm tra lại SSH Key của GitHub.")
            log_info("Bạn có thể chạy: eval $(ssh-agent -s) && ssh-add ~/.ssh/id_rsa")
            break # Lỗi này không thể tự sửa bằng git
            
        else:
            log_warning("Lỗi không xác định. Đang tự động dùng Force Push làm phương án cuối...")
            print(f"{Colors.WARNING}Chi tiết lỗi: {err.strip()}{Colors.ENDC}")
            force_pushed = True
        
        attempt += 1
        time.sleep(1)

    print("\n" + "=" * 56)
    if success:
        print(f"{Colors.BOLD}{Colors.GREEN} 🎉 DEPLOYMENT THÀNH CÔNG! CODE ĐÃ ĐƯỢC ĐẨY LÊN GITHUB. 🎉{Colors.ENDC}")
    else:
        print(f"{Colors.BOLD}{Colors.FAIL} ❌ DEPLOYMENT THẤT BẠI SAU {max_attempts} LẦN THỬ.{Colors.ENDC}")
    print("========================================================")

if __name__ == '__main__':
    try:
        deploy()
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Đã hủy quá trình deploy.{Colors.ENDC}")
        sys.exit(0)