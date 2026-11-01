//! Python bindings for the Lattice generation engine (`lattice._engine`).
use lattice_engine::{Assignment, Model, Options};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

type Pair = ((usize, usize), (usize, usize));

/// Generates a covering array. Returns (rows ordered by coverage, new tuples per row, valid tuples).
#[pyfunction]
#[pyo3(signature = (sizes, weights, strength, invalid_pairs, requires, higher_order, forced, *, seed, candidates, shrink_steps, patience))]
#[allow(clippy::too_many_arguments)]
fn generate(
    py: Python<'_>,
    sizes: Vec<usize>,
    weights: Vec<Vec<f64>>,
    strength: usize,
    invalid_pairs: Vec<Pair>,
    requires: Vec<Pair>,
    higher_order: Vec<(Vec<Assignment>, Assignment)>,
    forced: Vec<Vec<Assignment>>,
    seed: u64,
    candidates: usize,
    shrink_steps: u64,
    patience: u64,
) -> PyResult<(Vec<Vec<usize>>, Vec<usize>, usize)> {
    let model = Model { sizes, weights, strength, invalid_pairs, requires, higher_order, forced };
    let options = Options { seed, candidates: candidates.max(1), shrink_steps, patience };
    let result = py.detach(|| lattice_engine::generate(&model, &options));
    match result {
        Ok(generated) => Ok((generated.rows, generated.new_coverage, generated.valid_tuples)),
        Err(error) => Err(PyValueError::new_err(format!("{error:?}"))),
    }
}

#[pymodule]
fn _engine(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(generate, module)?)?;
    Ok(())
}
