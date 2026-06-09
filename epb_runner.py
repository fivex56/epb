# epb_runner.py
import os
import subprocess
import time
import json
import signal
import glob
import threading
import psutil
import argparse
from datetime import datetime, timedelta
from pathlib import Path

class ScraperManager:
    def __init__(self, check_interval=5, timeout_minutes=5, wait_minutes=2):
        self.check_interval = check_interval
        self.timeout_seconds = timeout_minutes * 60
        self.wait_seconds = wait_minutes * 60
        self.current_process = None
        self.running = False
        
    def find_scrapers(self):
        scrapers = glob.glob("*_scraper.py")
        # Исключаем базовые классы — они не скраперы
        scrapers = [s for s in scrapers if not s.startswith("base_")]
        return sorted(scrapers)
    
    def get_price_file(self, scraper_name):
        base_name = scraper_name.replace("_scraper.py", "")
        return f"{base_name}_prices.json"
    
    def get_file_mtime(self, filename):
        if os.path.exists(filename):
            return os.path.getmtime(filename)
        return None
    
    def needs_headful(self, scraper_path):
        """Проверяет, требует ли скрапер параметр --headful"""
        try:
            with open(scraper_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return 'playwright' in content or '--headful' in content or 'headful' in content
        except:
            return False
    
    def get_scraper_command(self, scraper_path):
        """Формирует команду для запуска скрапера."""
        base_cmd = ["python", scraper_path]
        # Больше не добавляем --headful автоматически.
        # Все скраперы должны работать в headless-режиме.
        # Для отладки используйте: python scraper.py --headful
        return base_cmd
    
    def run_external_script(self, script_name, args=None, timeout=300):
        """Запускает внешний скрипт и ждет его завершения"""
        if args is None:
            args = []
        
        print(f"Запускаем {script_name}...")
        
        try:
            if script_name.endswith('.py'):
                cmd = ["python", script_name] + args
            elif script_name.endswith('.bat'):
                cmd = ["cmd", "/c", script_name] + args  # Исправлено для bat файлов
            else:
                cmd = [script_name] + args
            
            env = os.environ.copy()
            env.setdefault("PYTHONIOENCODING", "utf-8")
            env.setdefault("PYTHONUTF8", "1")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                encoding="utf-8",
                errors="replace",
                env=env,           
            )

            
            # Ждем завершения процесса с таймаутом
            try:
                stdout, stderr = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                print(f"Таймаут выполнения {script_name}")
                process.kill()
                stdout, stderr = process.communicate()
            
            # Вывод с обработкой кодировки
            if stdout and stdout.strip():
                print(f"Вывод {script_name}:\n{stdout}")
            if stderr and stderr.strip():
                print(f"Ошибки {script_name}:\n{stderr}")
                
            return process.returncode == 0
            
        except Exception as e:
            print(f"Ошибка запуска {script_name}: {e}")
            return False
    
    def monitor_file_changes(self, price_file, start_time):
        initial_mtime = self.get_file_mtime(price_file)
        
        end_time = time.time() + self.timeout_seconds
        while time.time() < end_time and self.running:
            current_mtime = self.get_file_mtime(price_file)
            
            if current_mtime and current_mtime > start_time:
                print(f"Файл {price_file} изменен!")
                return True
            
            if self.current_process and self.current_process.poll() is not None:
                print("Процесс сборщика завершился")
                current_mtime = self.get_file_mtime(price_file)
                if current_mtime and current_mtime > start_time:
                    print(f"Файл {price_file} изменен после завершения процесса!")
                    return True
                break
            
            time.sleep(self.check_interval)
        
        return False
    
    def run_scraper(self, scraper_path):
        price_file = self.get_price_file(os.path.basename(scraper_path))
        start_time = time.time()
        
        command = self.get_scraper_command(scraper_path)
        print(f"Запускаем сборщик: {' '.join(command)}")
        print(f"Ожидаем изменения файла: {price_file}")
        
        try:
            self.current_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace'
            )
        except Exception as e:
            print(f"Ошибка запуска {scraper_path}: {e}")
            return False
        
        file_changed = self.monitor_file_changes(price_file, start_time)
        
        # Даем процессу немного времени на завершение
        if self.current_process and self.current_process.poll() is None:
            time.sleep(2)
        
        self.terminate_process()
        
        # Читаем вывод процесса
        stdout, stderr = "", ""
        try:
            if self.current_process.stdout:
                stdout = self.current_process.stdout.read()
            if self.current_process.stderr:
                stderr = self.current_process.stderr.read()
        except Exception as e:
            print(f"Ошибка чтения вывода процесса: {e}")
        
        if stdout and stdout.strip():
            print(f"Вывод сборщика:\n{stdout}")
        if stderr and stderr.strip():
            print(f"Ошибки сборщика:\n{stderr}")
        
        if file_changed:
            print("Сборщик успешно завершил работу (файл изменен)")
            return True
        else:
            print("Сборщик завершен по таймауту (файл не изменен)")
            return False
    
    def terminate_process(self):
        if self.current_process and self.current_process.poll() is None:
            print("Завершаем процесс сборщика...")
            try:
                # Пытаемся завершить gracefully
                self.current_process.terminate()
                self.current_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                print("Процесс не завершился, принудительное завершение...")
                try:
                    self.current_process.kill()
                    self.current_process.wait(timeout=5)
                except:
                    pass
            except Exception as e:
                print(f"Ошибка при завершении процесса: {e}")
                try:
                    self.current_process.kill()
                except:
                    pass
            
            self.current_process = None
    
    def wait_between_scrapers(self, seconds=None):
        """Ожидание между сборщиками с возможностью пропуска по пробелу."""
        if seconds is None:
            seconds = self.wait_seconds

        print(f"Ожидание {seconds//60} минут...")
        end_time = time.time() + seconds

        try:
            # Windows: безэховый опрос клавиатуры
            if os.name == 'nt':
                import msvcrt
                while time.time() < end_time and self.running:
                    if msvcrt.kbhit():
                        ch = msvcrt.getch()
                        # пропуск по пробелу
                        if ch in (b' ',):
                            break
                        # проглатываем расширенные коды
                        if ch in (b'\x00', b'\xe0'):
                            _ = msvcrt.getch()
                    time.sleep(0.1)
            else:
                # Unix-подобные: неблокирующее чтение stdin
                import sys, select, termios, tty
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                try:
                    tty.setcbreak(fd)
                    while time.time() < end_time and self.running:
                        r, _, _ = select.select([sys.stdin], [], [], 0.1)
                        if r:
                            ch = sys.stdin.read(1)
                            if ch == ' ':
                                break
                        time.sleep(0.1)
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except Exception:
            # На случай отсутствия доступа к stdin — обычный таймер
            while time.time() < end_time and self.running:
                time.sleep(1)
    
    def run_cycle(self):
        """Выполняет один полный цикл: все сборщики -> aggregate -> upload"""
        scrapers = self.find_scrapers()
        cycle_start = datetime.now()

        if not scrapers:
            print("Не найдено файлов сборщиков (*_scraper.py)")
            return False

        print(f"Найдено сборщиков: {len(scrapers)}")

        # Статистика цикла
        scraper_results = []

        # Запускаем все сборщики
        for i, scraper in enumerate(scrapers, 1):
            print(f"\n--- Запуск сборщика {i}/{len(scrapers)}: {scraper} ---")

            if not self.running:
                break

            start = time.time()
            success = self.run_scraper(scraper)
            elapsed = time.time() - start

            scraper_results.append({
                "scraper": scraper,
                "success": success,
                "elapsed_sec": round(elapsed, 1)
            })

            if success:
                print(f"[OK] {scraper} ({elapsed:.0f}s)")
            else:
                print(f"[FAIL] {scraper} ({elapsed:.0f}s)")

            if self.running and i < len(scrapers):
                self.wait_between_scrapers()

        # Запускаем aggregate.py
        aggregate_success = False
        fill_success = False
        if self.running:
            print("\n--- Запуск агрегации данных ---")
            aggregate_success = self.run_external_script("aggregate.py", timeout=120)
            if aggregate_success:
                print("[OK] Aggregation done")
                # Fill missing prices with estimates
                fill_success = self.run_external_script("fill_prices.py", timeout=60)
                if fill_success:
                    print("[OK] Price filling done")
                else:
                    print("[FAIL] Price filling error")
            else:
                print("[FAIL] Aggregation error")

            if self.running:
                self.wait_between_scrapers(30)

        # Запуск инжеста истории
        ingest_success = False
        if self.running:
            print("\n--- Запуск инжеста истории ---")
            ingest_success = self.run_external_script("epb_ingest.py", ["--once"], timeout=180)
            if ingest_success:
                print("[OK] History rebuilt")
            else:
                print("[FAIL] Ingest error")

        # Запускаем run_upload.bat
        upload_success = False
        if self.running and os.path.exists("run_upload.bat"):
            print("\n--- Запуск загрузки данных ---")
            upload_success = self.run_external_script("run_upload.bat", timeout=300)
            if upload_success:
                print("[OK] Upload done")
            else:
                print("[FAIL] Upload error")

        # --- Итоговый отчёт ---
        cycle_elapsed = (datetime.now() - cycle_start).total_seconds()
        ok = sum(1 for r in scraper_results if r["success"])
        fail = len(scraper_results) - ok

        print(f"\n{'='*60}")
        print(f"ИТОГИ ЦИКЛА (за {cycle_elapsed:.0f}с)")
        print(f"  Scrapers: {ok} ok, {fail} fail, {len(scraper_results)} total")
        print(f"  Aggregate: {'OK' if aggregate_success else 'FAIL'}")
        print(f"  Fill:      {'OK' if fill_success else 'FAIL'}")
        print(f"  Ingest:    {'OK' if ingest_success else 'FAIL'}")
        print(f"  Upload:    {'OK' if upload_success else 'FAIL'}")
        print(f"{'='*60}")

        # Пишем status.json для мониторинга
        self._write_status(cycle_start, scraper_results,
                          aggregate_success, fill_success, ingest_success, upload_success)

        return aggregate_success

    def _write_status(self, cycle_start, scraper_results,
                      aggregate_ok, fill_ok, ingest_ok, upload_ok):
        """Пишет status.json с результатами последнего цикла."""
        try:
            status = {
                "cycle_start": cycle_start.isoformat(),
                "cycle_end": datetime.now().isoformat(),
                "scrapers": scraper_results,
                "scrapers_ok": sum(1 for r in scraper_results if r["success"]),
                "scrapers_fail": sum(1 for r in scraper_results if not r["success"]),
                "aggregate_ok": aggregate_ok,
                "fill_ok": fill_ok,
                "ingest_ok": ingest_ok,
                "upload_ok": upload_ok,
            }
            with open("status.json", "w", encoding="utf-8") as f:
                json.dump(status, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def run(self, continuous=False):
        """Основной цикл работы"""
        self.running = True
        
        cycle_count = 0
        while self.running:
            cycle_count += 1
            print(f"\n{'='*60}")
            print(f"НАЧАЛО ЦИКЛА {cycle_count}")
            print(f"{'='*60}")
            
            success = self.run_cycle()
            
            if not continuous:
                break
                
            if self.running:
                print(f"\nЦикл {cycle_count} завершен. Ожидание перед следующим циклом...")
                # Ждем 25 минут между циклами
                self.wait_between_scrapers(1500)
    
    def stop(self):
        print("Остановка менеджера...")
        self.running = False
        self.terminate_process()

def main():
    try:
        import psutil
    except ImportError:
        print("Установите psutil: pip install psutil")
        return
    
    parser = argparse.ArgumentParser(description='Менеджер запуска сборщиков цен на энергию')
    parser.add_argument('--timeout', type=int, default=5, help='Таймаут выполнения сборщика в минутах')
    parser.add_argument('--wait', type=int, default=2, help='Время ожидания между сборщиками в минутах')
    parser.add_argument('--check-interval', type=int, default=5, help='Интервал проверки файлов в секундах')
    parser.add_argument('--once', action='store_true', help='Запустить только один цикл и завершить работу')
    parser.add_argument('--continuous', action='store_true', help='Работать в непрерывном режиме (по умолчанию)')
    
    args = parser.parse_args()
    
    # По умолчанию работаем в непрерывном режиме
    continuous = not args.once if args.once else True
    
    manager = ScraperManager(
        check_interval=args.check_interval,
        timeout_minutes=args.timeout,
        wait_minutes=args.wait
    )
    
    try:
        print("Запуск менеджера сборщиков...")
        print("Для остановки нажмите Ctrl+C")
        manager.run(continuous=continuous)
        
    except KeyboardInterrupt:
        print("\nОстановка по запросу пользователя...")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        manager.stop()
        print("Менеджер остановлен.")

if __name__ == "__main__":
    main()