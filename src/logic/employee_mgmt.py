"""
Employee management business logic.
"""
from typing import List, Optional
import random
import string
import config
from src.database.connection import db
from src.models.employee import Employee


class EmployeeService:
    """Service class for employee operations."""
    
    def __init__(self):
        self.db = db
    
    def generate_employee_id(self) -> str:
        """Generate a unique employee ID."""
        while True:
            digits = ''.join(random.choice(string.digits) for _ in range(6))
            emp_id = f"EMP{digits}"
            if not self.get_employee_by_id(emp_id):
                return emp_id
    
    def authenticate(self, emp_id: str, password: str) -> Optional[Employee]:
        """Authenticate an employee."""
        employee = self.get_employee_by_id(emp_id)
        
        if employee and employee.verify_password(password):
            return employee
        return None
    
    def get_all_employees(self) -> List[Employee]:
        """Get all employees."""
        query = "SELECT * FROM employee ORDER BY name"
        results = self.db.execute_query(query)
        return [Employee.from_db_row(row) for row in results]
    
    def get_employee_by_id(self, emp_id: str) -> Optional[Employee]:
        """Get employee by ID."""
        query = "SELECT * FROM employee WHERE emp_id = ?"
        results = self.db.execute_query(query, (emp_id,))
        
        if results:
            return Employee.from_db_row(results[0])
        return None
    
    def search_employees(self, search_term: str) -> List[Employee]:
        """Search employees by name or employee ID."""
        query = """
            SELECT * FROM employee 
            WHERE emp_id LIKE ? OR name LIKE ?
            ORDER BY name
        """
        search_pattern = f"%{search_term}%"
        results = self.db.execute_query(query, (search_pattern, search_pattern))
        return [Employee.from_db_row(row) for row in results]
    
    def get_employees_by_role(self, role: str) -> List[Employee]:
        """Get employees filtered by role."""
        query = "SELECT * FROM employee WHERE role = ? ORDER BY name"
        results = self.db.execute_query(query, (role,))
        return [Employee.from_db_row(row) for row in results]
    
    def add_employee(self, employee: Employee) -> bool:
        """Add a new employee."""
        try:
            query = """
                INSERT INTO employee (
                    emp_id, name, password, role, contact_num,
                    address, designation, aadhar_number
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            self.db.execute_insert(
                query,
                (
                    employee.emp_id, employee.get_full_name(),
                    employee.password, employee.role, employee.contact_number,
                    employee.address, employee.designation,
                    employee.aadhar_number
                )
            )
            return True
        except Exception as e:
            print(f"Error adding employee: {str(e)}")
            return False
    
    def update_employee(self, employee: Employee) -> bool:
        """Update an existing employee."""
        try:
            query = """
                UPDATE employee 
                SET name = ?, password = ?, role = ?,
                    contact_num = ?, address = ?, 
                    designation = ?, aadhar_number = ?
                WHERE emp_id = ?
            """
            
            self.db.execute_update(
                query,
                (
                    employee.get_full_name(), employee.password,
                    employee.role, employee.contact_number,
                    employee.address, employee.designation, employee.aadhar_number,
                    employee.emp_id
                )
            )
            return True
        except Exception as e:
            print(f"Error updating employee: {str(e)}")
            return False
    
    def delete_employee(self, emp_id: str) -> bool:
        """Delete an employee."""
        try:
            query = "DELETE FROM employee WHERE emp_id = ?"
            self.db.execute_update(query, (emp_id,))
            return True
        except Exception as e:
            print(f"Error deleting employee: {str(e)}")
            return False
    
    def change_password(self, emp_id: str, new_password: str) -> bool:
        """Change employee password."""
        try:
            hashed_password = Employee.hash_password(new_password)
            query = "UPDATE employee SET password = ? WHERE emp_id = ?"
            self.db.execute_update(query, (hashed_password, emp_id))
            return True
        except Exception as e:
            print(f"Error changing password: {str(e)}")
            return False
    
    def get_total_employee_count(self) -> int:
        """Get total number of employees."""
        query = "SELECT COUNT(*) as count FROM employee"
        results = self.db.execute_query(query)
        return results[0]['count'] if results else 0
    
    def get_admin_count(self) -> int:
        """Get number of admin users."""
        query = "SELECT COUNT(*) as count FROM employee WHERE role = 'Admin'"
        results = self.db.execute_query(query)
        return results[0]['count'] if results else 0
