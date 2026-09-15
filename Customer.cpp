#include "Customer.h"

#include <ctime>
#include <iomanip>
#include <sstream>

// ---------------------------------------------------------------------------
// Date
// ---------------------------------------------------------------------------

Date::Date() : day(1), month(1), year(2000) {}

Date::Date(int day, int month, int year)
    : day(day), month(month), year(year) {}

Date Date::today() {
    std::time_t now = std::time(nullptr);
    std::tm* local = std::localtime(&now);

    // tm_mon counts from 0, and tm_year counts from 1900.
    return Date(local->tm_mday, local->tm_mon + 1, local->tm_year + 1900);
}

std::string Date::toString() const {
    std::ostringstream out;
    out << std::setfill('0')
        << std::setw(2) << day << '-'
        << std::setw(2) << month << '-'
        << std::setw(4) << year;
    return out.str();
}

// ---------------------------------------------------------------------------
// Customer
// ---------------------------------------------------------------------------

Customer::Customer()
    : id(0), name(""), phone(""), email(""), address(""), registrationDate() {}

Customer::Customer(int id,
                   const std::string& name,
                   const std::string& phone,
                   const std::string& email,
                   const std::string& address,
                   const Date& registrationDate)
    : id(id),
      name(name),
      phone(phone),
      email(email),
      address(address),
      registrationDate(registrationDate) {}

int Customer::getId() const { return id; }
std::string Customer::getName() const { return name; }
std::string Customer::getPhone() const { return phone; }
std::string Customer::getEmail() const { return email; }
std::string Customer::getAddress() const { return address; }
Date Customer::getRegistrationDate() const { return registrationDate; }

void Customer::setName(const std::string& name) { this->name = name; }
void Customer::setPhone(const std::string& phone) { this->phone = phone; }
void Customer::setEmail(const std::string& email) { this->email = email; }
void Customer::setAddress(const std::string& address) { this->address = address; }

std::string Customer::toDisplayString() const {
    std::ostringstream out;
    out << "Customer ID   : " << id << '\n'
        << "Name          : " << name << '\n'
        << "Phone         : " << phone << '\n'
        << "Email         : " << email << '\n'
        << "Address       : " << address << '\n'
        << "Registered On : " << registrationDate.toString();
    return out.str();
}
