from tempfile import NamedTemporaryFile
from click.testing import CliRunner
from clarite.cli.commands import load_cli


def test_from_tsv():
   output = NamedTemporaryFile()
   runner = CliRunner()
   result = runner.invoke(load_cli, ['from-tsv', '../test_data_files/nhanes_subset/data.txt', str(output.name)])
   assert result.exit_code == 0
   assert result.output.startswith("Loaded 9,063 observations of 11 variables")


def test_from_csv():
   output = NamedTemporaryFile()
   runner = CliRunner()
   result = runner.invoke(load_cli, ['from-csv', '../test_data_files/nhanes_data.csv', str(output.name)])
   assert result.exit_code == 0
   assert result.output.startswith("Loaded 8,591 observations of 6 variables")
