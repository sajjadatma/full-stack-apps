from __future__ import annotations

import json
import uuid
from collections.abc import Callable

import pytest

from app.models import Product, ProductImage, TargetSurface
from app.services import image_edit_prompts
from app.services.image_edit import ImageEditInstructions
from app.services.image_edit_prompts import (
    PROMPT_VERSION,
    ImageEditPrompt,
    build_floor_prompt,
    build_wall_prompt,
)


def _product(**updates: object) -> Product:
    values: dict[str, object] = {
        "name": "Harbor Tile",
        "id": uuid.UUID("532dc47d-8a0f-43ce-b5c8-e058ad8a9901"),
        "sku": "HARBOR-01",
        "slug": "harbor-tile",
        "category_id": uuid.UUID("c4fbef35-03b0-4c17-8998-b35d70de0a43"),
        "material": "porcelain",
        "finish": "matte",
        "color_family": "warm grey",
        "width_mm": 600,
        "height_mm": 1200,
        "thickness_mm": 9,
        "rectified": True,
    }
    values.update(updates)
    return Product(**values)  # type: ignore[arg-type]


def _product_image() -> ProductImage:
    return ProductImage(
        id=uuid.UUID("120e3e67-c94b-40e3-9ab5-51b21da26899"),
        product_id=uuid.UUID("532dc47d-8a0f-43ce-b5c8-e058ad8a9901"),
        storage_key="private/catalog/harbor-tile-secret-path.png",
        content_type="image/png",
        url="https://private.example/secret-image-url",
    )


@pytest.mark.parametrize(
    ("surface", "builder"),
    [
        (TargetSurface.FLOOR, build_floor_prompt),
        (TargetSurface.WALL, build_wall_prompt),
    ],
)
def test_prompt_encodes_all_scene_preservation_rules(
    surface: TargetSurface,
    builder: Callable[[Product, ProductImage], ImageEditPrompt],
) -> None:
    result = builder(_product(), _product_image())
    prompt = _all_text(result.instructions).lower()

    assert result.metadata["target_surface"] == surface.value
    for required_rule in (
        "camera position and angle",
        "perspective and all room geometry",
        "furniture and object positions",
        "windows, doors, openings, ceiling, fixtures",
        "modify only the requested target surface",
        "keep every non-target surface visually unchanged",
        "do not add or remove unrelated objects",
        "do not redesign the room",
        "when uncertain, preserve the original scene",
        "do not change global exposure, white balance, saturation, or color grading",
    ):
        assert required_rule in prompt


def test_floor_builder_changes_only_visible_floor_and_preserves_walls() -> None:
    result = build_floor_prompt(_product(), _product_image())
    prompt = _all_text(result.instructions).lower()

    assert "floor" in prompt
    assert "modify only the visible floor" in prompt
    assert "preserve all walls" in prompt
    for requirement in (
        "tile scale",
        "repetition",
        "grout",
        "perspective",
        "edges",
        "occlusion",
    ):
        assert requirement in prompt


def test_wall_builder_limits_change_and_protects_floor_and_obstacles() -> None:
    result = build_wall_prompt(_product(), _product_image())
    prompt = _all_text(result.instructions).lower()

    assert "wall" in prompt
    assert "only the intended visible wall surface" in prompt
    assert "preserve the floor" in prompt
    for protected in (
        "doors",
        "windows",
        "trim",
        "switches",
        "fixtures",
        "artwork",
        "furniture",
        "openings",
    ):
        assert protected in prompt
    for requirement in ("scale", "repetition", "grout", "perspective", "occlusion"):
        assert requirement in prompt


def test_product_image_is_reference_and_available_metadata_is_included() -> None:
    result = build_floor_prompt(_product(), _product_image())
    prompt = _all_text(result.instructions)

    assert "selected ProductImage" in prompt
    assert "visual material reference" in prompt
    assert "dimensions: 600 x 1200 mm" in prompt
    assert "thickness: 9 mm" in prompt
    assert "material: porcelain" in prompt
    assert "finish: matte" in prompt
    assert "color: warm grey" in prompt
    assert "rectified: yes" in prompt
    assert result.metadata["product_image_id"] == "120e3e67-c94b-40e3-9ab5-51b21da26899"
    assert result.metadata["used_product_attributes"] == {
        "width_mm": 600,
        "height_mm": 1200,
        "thickness_mm": 9,
        "material": "porcelain",
        "finish": "matte",
        "color_family": "warm grey",
        "rectified": True,
    }


def test_missing_dimensions_and_metadata_are_not_fabricated() -> None:
    result = build_wall_prompt(
        _product(
            material=None,
            finish=None,
            color_family=None,
            width_mm=None,
            height_mm=None,
            thickness_mm=None,
        ),
        _product_image(),
    )
    prompt = _all_text(result.instructions)

    assert "dimensions:" not in prompt
    assert "thickness:" not in prompt
    assert "material:" not in prompt
    assert "finish:" not in prompt
    assert "color:" not in prompt
    assert "without inventing measurements" in prompt
    assert result.metadata["used_product_attributes"] == {"rectified": True}


def test_identical_structured_inputs_produce_identical_provider_neutral_result() -> (
    None
):
    product = _product()
    image = _product_image()

    first = build_floor_prompt(product, image)
    second = build_floor_prompt(product, image)

    assert first == second
    assert isinstance(first.instructions, ImageEditInstructions)
    assert first.prompt_version == PROMPT_VERSION == "tilevision-v1"
    json.dumps(first.metadata)
    assert "openai" not in vars(image_edit_prompts)


def test_prompt_and_metadata_exclude_image_bytes_urls_and_storage_secrets() -> None:
    image = _product_image()
    result = build_floor_prompt(_product(), image)
    prompt = _all_text(result.instructions)
    serialized_metadata = repr(result.metadata)

    for forbidden in (
        image.storage_key,
        image.url,
        "OPENAI_API_KEY",
        "sk-secret",
        "\x89PNG",
    ):
        assert forbidden not in prompt
        assert forbidden not in serialized_metadata


def test_prompt_builders_have_explicit_distinct_surface_behavior() -> None:
    floor = build_floor_prompt(_product(), _product_image())
    wall = build_wall_prompt(_product(), _product_image())

    assert floor.metadata["target_surface"] == "FLOOR"
    assert wall.metadata["target_surface"] == "WALL"
    assert floor.instructions != wall.instructions


def _all_text(instructions: ImageEditInstructions) -> str:
    return "\n".join((instructions.instruction, *instructions.constraints))
