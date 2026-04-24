from typing import Annotated

import nh3
from pydantic import EmailStr, AfterValidator

String = Annotated[str, AfterValidator(lambda v: nh3.clean(v))]
EmailString = Annotated[
    EmailStr, AfterValidator(lambda v: nh3.clean(v).lower().strip())
]
