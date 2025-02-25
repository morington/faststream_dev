from typing import Optional, Literal

from src.infrastructure.logger.main import LoggerReg, SetupLogger


class InitLoggers:

    main = LoggerReg(name="MAIN", level=LoggerReg.Level.DEBUG)

    def __init__(
            self,
            *,
            developer_mode: bool = True,
            select_format: Optional[Literal['console', 'jsonformat']] = None,
            ensure_ascii: bool = True
    ) -> None:
        SetupLogger(
            developer_mode=developer_mode,
            name_registration=[
                self.main,
            ],
            select_format=select_format,
            ensure_ascii=ensure_ascii
        )


if __name__ == "__main__":
    test_logger = InitLoggers.main

    print(type(test_logger))    # <class 'src.infrastructure.logging.main.LoggerReg'>
    print(test_logger)          # LoggerReg(name='MAIN', level=<Level.DEBUG: 'DEBUG'>, propagate=False, write_file=False)

    test_logger_name = InitLoggers.main.name

    print(type(test_logger_name))   # <class 'str'>
    print(test_logger_name)         # MAIN
