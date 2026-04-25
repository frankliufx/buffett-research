# Buffett Research — common dev commands.
# Run from project root.

.PHONY: types types-check dev-streamlit dev-api dev-web install

# ---------------------------------------------------------------- type sync ---

# Regenerate web/lib/types.generated.ts from the Pydantic schemas.
# Pydantic is the single source of truth; the .ts file is committed.
types:
	@python scripts/generate_types.py

# Verify the committed types.generated.ts is up to date with schemas/.
# Fails (non-zero exit) if regeneration would change the file — useful in CI.
types-check:
	@python scripts/generate_types.py
	@git diff --exit-code web/lib/types.generated.ts \
		|| (echo "❌ types.generated.ts is stale. Run 'make types' and commit." && exit 1)
	@echo "✅ types.generated.ts is in sync with schemas/"

# ----------------------------------------------------------------- dev runs ---

dev-streamlit:
	streamlit run app.py

dev-api:
	uvicorn api.main:app --port 8502 --reload

dev-web:
	cd web && npm run dev

# Install all toolchains needed for type generation + dev.
install:
	pip install -r requirements.txt pydantic-to-typescript
	cd web && npm install
