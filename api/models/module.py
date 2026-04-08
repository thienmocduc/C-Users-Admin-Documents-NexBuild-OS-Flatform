"""Ecosystem module models."""
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.core.database import Base


class Module(Base):
    __tablename__ = "modules"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    num: Mapped[str | None] = mapped_column(String(5))
    tag: Mapped[str | None] = mapped_column(String(100))
    model: Mapped[str | None] = mapped_column(String(100))
    hook: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    icon_svg: Mapped[str | None] = mapped_column(Text)
    icon_bg: Mapped[str | None] = mapped_column(String(20))
    icon_border: Mapped[str | None] = mapped_column(String(20))
    cta_bg: Mapped[str | None] = mapped_column(String(100))
    color: Mapped[str | None] = mapped_column(String(20))
    gradient: Mapped[str | None] = mapped_column(String(200))
    file_url: Mapped[str | None] = mapped_column(String(255))
    pricing_label: Mapped[str | None] = mapped_column(String(100))
    pricing_detail: Mapped[str | None] = mapped_column(String(200))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    pains = relationship("ModulePain", back_populates="module", lazy="selectin")
    results = relationship("ModuleResult", back_populates="module", lazy="selectin")


class ModulePain(Base):
    __tablename__ = "module_pains"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    module_id: Mapped[str] = mapped_column(String(20), ForeignKey("modules.id", ondelete="CASCADE"), nullable=False, index=True)
    before_title: Mapped[str | None] = mapped_column(String(200))
    before_desc: Mapped[str | None] = mapped_column(Text)
    after_title: Mapped[str | None] = mapped_column(String(200))
    after_desc: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    module = relationship("Module", back_populates="pains")


class ModuleResult(Base):
    __tablename__ = "module_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    module_id: Mapped[str] = mapped_column(String(20), ForeignKey("modules.id", ondelete="CASCADE"), nullable=False, index=True)
    emoji: Mapped[str | None] = mapped_column(String(10))
    title: Mapped[str | None] = mapped_column(String(200))
    kpi: Mapped[str | None] = mapped_column(String(100))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    module = relationship("Module", back_populates="results")
