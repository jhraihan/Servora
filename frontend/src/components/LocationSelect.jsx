import PropTypes from "prop-types";

import { flattenAreas, useLocationTree } from "../hooks/useCatalogue";

export default function LocationSelect({ id, value, onChange, placeholder = "Any area", required = false }) {
  const { data: tree, isLoading } = useLocationTree();
  const rows = flattenAreas(tree);
  const thanas = [...new Set(rows.map((r) => r.thanaName))];

  return (
    <select
      id={id}
      className="input"
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
      disabled={isLoading}
      required={required}
    >
      <option value="">{isLoading ? "Loading areas…" : placeholder}</option>
      {thanas.map((thana) => (
        <optgroup key={thana} label={thana}>
          {rows
            .filter((r) => r.thanaName === thana)
            .map((r) => (
              <option key={r.id} value={r.id}>
                {r.level === "thana" ? `All of ${r.label}` : r.label}
              </option>
            ))}
        </optgroup>
      ))}
    </select>
  );
}

LocationSelect.propTypes = {
  id: PropTypes.string.isRequired,
  value: PropTypes.number,
  onChange: PropTypes.func.isRequired,
  placeholder: PropTypes.string,
  required: PropTypes.bool,
};
