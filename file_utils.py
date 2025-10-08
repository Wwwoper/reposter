import asyncio
import hashlib
from pathlib import Path
from typing import Optional

from my_logger import logger


class FileValidator:
    """Класс для валидации и проверки файлов изображений"""
    
    # Максимальный размер файла (50 MB для ВК)
    MAX_FILE_SIZE = 50 * 1024 * 1024
    
    # Поддерживаемые форматы
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}
    
    @staticmethod
    async def wait_for_file_ready(
        file_path: str,
        max_attempts: int = 5,
        initial_delay: float = 0.2
    ) -> bool:
        """
        Ожидает полной записи файла на диск с экспоненциальной задержкой
        
        Args:
            file_path: путь к файлу
            max_attempts: максимальное количество попыток
            initial_delay: начальная задержка в секундах
            
        Returns:
            True если файл готов, False иначе
        """
        path = Path(file_path)
        prev_size = 0
        
        for attempt in range(max_attempts):
            try:
                # Проверка существования файла
                if not path.exists():
                    logger.warning(
                        f"Файл {file_path} еще не существует (попытка {attempt + 1}/{max_attempts})"
                    )
                    await asyncio.sleep(initial_delay * (2 ** attempt))
                    continue
                
                # Получение размера файла
                current_size = path.stat().st_size
                
                # Проверка что размер не 0
                if current_size == 0:
                    logger.warning(
                        f"Файл {file_path} пустой (попытка {attempt + 1}/{max_attempts})"
                    )
                    await asyncio.sleep(initial_delay * (2 ** attempt))
                    continue
                
                # Попытка открыть файл для чтения
                with open(file_path, 'rb') as f:
                    # Читаем небольшую часть для проверки доступности
                    data = f.read(8192)
                    if not data:
                        logger.warning(
                            f"Не удалось прочитать данные из {file_path} "
                            f"(попытка {attempt + 1}/{max_attempts})"
                        )
                        await asyncio.sleep(initial_delay * (2 ** attempt))
                        continue
                
                # Проверка стабильности размера
                # Если размер не изменился с предыдущей попытки - файл записан
                if attempt > 0 and current_size == prev_size:
                    logger.debug(
                        f"Файл {file_path} готов к использованию "
                        f"(размер: {current_size} байт, попытка {attempt + 1})"
                    )
                    return True
                
                prev_size = current_size
                
                # Небольшая задержка перед следующей проверкой
                if attempt < max_attempts - 1:
                    await asyncio.sleep(initial_delay * (2 ** attempt))
                    
            except (IOError, OSError) as e:
                logger.warning(
                    f"Ошибка доступа к файлу {file_path} "
                    f"(попытка {attempt + 1}/{max_attempts}): {e}"
                )
                if attempt < max_attempts - 1:
                    await asyncio.sleep(initial_delay * (2 ** attempt))
        
        logger.error(f"Файл {file_path} не готов после {max_attempts} попыток")
        return False
    
    @staticmethod
    async def validate_image_file(file_path: str) -> bool:
        """
        Полная валидация файла изображения
        
        Args:
            file_path: путь к файлу
            
        Returns:
            True если файл валиден, False иначе
        """
        path = Path(file_path)
        
        # Проверка существования
        if not path.exists():
            logger.error(f"Файл {file_path} не существует")
            return False
        
        # Проверка расширения
        if path.suffix.lower() not in FileValidator.ALLOWED_EXTENSIONS:
            logger.error(
                f"Неподдерживаемый формат файла: {path.suffix}. "
                f"Разрешены: {FileValidator.ALLOWED_EXTENSIONS}"
            )
            return False
        
        # Проверка размера
        try:
            file_size = path.stat().st_size
            
            if file_size == 0:
                logger.error(f"Файл {file_path} пустой (0 байт)")
                return False
            
            if file_size > FileValidator.MAX_FILE_SIZE:
                logger.error(
                    f"Файл {file_path} слишком большой: {file_size} байт "
                    f"(максимум: {FileValidator.MAX_FILE_SIZE} байт)"
                )
                return False
            
            logger.debug(f"Файл {file_path} прошел валидацию (размер: {file_size} байт)")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при валидации файла {file_path}: {e}")
            return False
    
    @staticmethod
    async def calculate_file_hash(file_path: str) -> Optional[str]:
        """
        Вычисляет MD5 хеш файла для проверки целостности
        
        Args:
            file_path: путь к файлу
            
        Returns:
            MD5 хеш или None в случае ошибки
        """
        try:
            md5_hash = hashlib.md5()
            
            def _compute_hash():
                with open(file_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(8192), b''):
                        md5_hash.update(chunk)
                return md5_hash.hexdigest()
            
            hash_value = await asyncio.to_thread(_compute_hash)
            logger.debug(f"MD5 хеш файла {file_path}: {hash_value}")
            return hash_value
            
        except Exception as e:
            logger.error(f"Ошибка вычисления хеша для {file_path}: {e}")
            return None


async def prepare_file_for_upload(file_path: str) -> bool:
    """
    Комплексная подготовка файла к загрузке
    
    Args:
        file_path: путь к файлу
        
    Returns:
        True если файл готов, False иначе
    """
    validator = FileValidator()
    
    # Шаг 1: Ожидание готовности файла
    logger.debug(f"Ожидание готовности файла {file_path}...")
    if not await validator.wait_for_file_ready(file_path):
        logger.error(f"Файл {file_path} не готов к загрузке")
        return False
    
    # Шаг 2: Валидация файла
    logger.debug(f"Валидация файла {file_path}...")
    if not await validator.validate_image_file(file_path):
        logger.error(f"Файл {file_path} не прошел валидацию")
        return False
    
    # Шаг 3: Вычисление хеша для контроля целостности
    file_hash = await validator.calculate_file_hash(file_path)
    if not file_hash:
        logger.warning(f"Не удалось вычислить хеш для {file_path}, но продолжаем")
    
    logger.info(f"Файл {file_path} готов к загрузке")
    return True