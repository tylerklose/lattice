//! Python bindings for the Lattice engine (`lattice._engine`).
//!
//! `Model(sizes, weights, strength, invalid_pairs, requires, higher_order, forced)`
//! takes a schema compiled to the engine's constraint primitives and answers:
//! `feasibility()` (raises on an impossible forced interaction or an
//! unsatisfiable model), `can_complete(assignments)`, and `generate(...)`.
use lattice_engine::{Assignment, Engine, Error, Model as EngineModel, Options};
use pyo3::create_exception;
use pyo3::exceptions::{PyException, PyValueError};
use pyo3::prelude::*;

type Pair = (Assignment, Assignment);

create_exception!(_engine, ForcedInfeasible, PyException, "A forced interaction can't appear in any valid row; args[0] is its index.");
create_exception!(_engine, NoValidAssignments, PyException, "No row satisfies every constraint.");

fn to_py(error: Error) -> PyErr {
    match error {
        Error::ForcedInfeasible(index) => ForcedInfeasible::new_err(index),
        Error::NoValidAssignments => NoValidAssignments::new_err(()),
        other => PyValueError::new_err(format!("{other:?}")),
    }
}

#[pyclass(module = "lattice._engine")]
struct Model {
    engine: Engine,
}

#[pymethods]
impl Model {
    #[new]
    fn new(
        sizes: Vec<usize>,
        weights: Vec<Vec<f64>>,
        strength: usize,
        invalid_pairs: Vec<Pair>,
        requires: Vec<Pair>,
        higher_order: Vec<(Vec<Assignment>, Assignment)>,
        forced: Vec<Vec<Assignment>>,
    ) -> PyResult<Self> {
        let model = EngineModel { sizes, weights, strength, invalid_pairs, requires, higher_order, forced };
        Ok(Model { engine: Engine::new(model).map_err(to_py)? })
    }

    fn feasibility(&mut self) -> PyResult<()> {
        self.engine.feasibility().map_err(to_py)
    }

    fn can_complete(&mut self, assignments: Vec<Assignment>) -> PyResult<bool> {
        self.engine.can_complete(&assignments).map_err(to_py)
    }

    /// Returns (rows ordered by coverage, new tuples per row, valid tuples).
    #[pyo3(signature = (*, seed, candidates, shrink_steps, patience))]
    fn generate(
        &mut self,
        py: Python<'_>,
        seed: u64,
        candidates: usize,
        shrink_steps: u64,
        patience: u64,
    ) -> PyResult<(Vec<Vec<usize>>, Vec<usize>, usize)> {
        let options = Options { seed, candidates: candidates.max(1), shrink_steps, patience };
        let engine = &mut self.engine;
        let result = py.detach(|| engine.generate(&options)).map_err(to_py)?;
        Ok((result.rows, result.new_coverage, result.valid_tuples))
    }
}

#[pymodule]
fn _engine(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<Model>()?;
    module.add("ForcedInfeasible", module.py().get_type::<ForcedInfeasible>())?;
    module.add("NoValidAssignments", module.py().get_type::<NoValidAssignments>())?;
    Ok(())
}
