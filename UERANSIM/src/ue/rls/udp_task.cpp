//
// This file is a part of UERANSIM project.
// Copyright (c) 2023 ALİ GÜNGÖR.
//
// https://github.com/aligungr/UERANSIM/
// See README, LICENSE, and CONTRIBUTING files for licensing details.
//

#include "udp_task.hpp"

#include <cstdint>
#include <cstring>
#include <set>

#include <ue/nts.hpp>
#include <utils/common.hpp>
#include <utils/constants.hpp>

// added by Henok
#include <iostream>
#include <random>
#include <chrono>
#include <cmath>
#include <vector>
#include <string>
#include <prometheus/exposer.h>
#include <prometheus/counter.h>
#include <prometheus/gauge.h>
#include <prometheus/registry.h>

static constexpr const int BUFFER_SIZE = 16384;
static constexpr const int LOOP_PERIOD = 1000;
static constexpr const int RECEIVE_TIMEOUT = 200;
static constexpr const int HEARTBEAT_THRESHOLD = 2000; // (LOOP_PERIOD + RECEIVE_TIMEOUT)'dan büyük olmalı
DoubleVector3 Home;  // added by Henok
DoubleVector3 Work;  // added by Henok
namespace nr::ue
{

RlsUdpTask::RlsUdpTask(TaskBase *base, RlsSharedContext *shCtx, const std::vector<std::string> &searchSpace)
    : m_server{}, m_ctlTask{}, m_shCtx{shCtx}, m_searchSpace{}, m_cells{}, m_cellIdToSti{}, m_lastLoop{},
      m_cellIdCounter{}
{
    m_logger = base->logBase->makeUniqueLogger(base->config->getLoggerPrefix() + "rls-udp");

    m_server = new udp::UdpServer();

    for (auto &ip : searchSpace)
        m_searchSpace.emplace_back(ip, cons::RadioLinkPort);
    // modified by Henok
   
    m_simPos = base->config->simpos;
    m_supi = base->config->supi;
    simPos.x = (double) m_simPos.x;
    simPos.y = (double) m_simPos.y;
    simPos.z = (double) m_simPos.z;
    home.x = (double) base->config->home.x;
    home.y = (double) base->config->home.y;
    home.z = (double) base->config->home.z;
    work.x = (double) base->config->work.x;
    work.y = (double) base->config->work.y;
    work.z = (double) base->config->work.z;
    std::cout << base->config->work.x << std::endl;

    //  initialize Prometheus
    registry = std::make_shared<prometheus::Registry>();
    int port = 8080 + (m_supi->value.back() - '0');
    exposer = std::make_shared<prometheus::Exposer>("0.0.0.0:" + std::to_string(port));
    exposer->RegisterCollectable(registry);

    // Create a counter family
    destination_visits_family = &prometheus::BuildCounter()
        .Name("ue_destination_visits_total")
        .Help("Total number of times a UE has reached a destination")
        .Register(*registry);
    
    // modified by Henok

}

void RlsUdpTask::onStart()
{
}



///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////




////////////////////added by Henok



std::random_device rd;  // added by Henok
std::mt19937 gen(rd());  // added by Henok


// Constants and utility functions
const double min_pos = 0;
const double max_pos = 150;
const double min_speed = 0.05;
const double max_speed = 0.1;
// const double min_speed = 0.5;
// const double max_speed = 2.0;
const double hr = 3600;

double calculateDistance(double x1, double y1, double x2, double y2) {
    return sqrt(pow(x2 - x1, 2) + pow(y2 - y1, 2));
}

enum class TimeOfDay {
    NIGHT,
    MORNING,
    LUNCH,
    AFTERNOON,
    EVENING
};

struct ActivityLocation {
    double x, y;
    std::string type;
    TimeOfDay preferredTime;
    // double duration;
    struct {
        double mean;
        double stddev;
    } duration;
    double probability;  // Base probability of visiting this location
};

// function to strip numbers from type names
std::string getBaseType(const std::string& type) {
    std::string baseType;
    for (char c : type) {
        if (!std::isdigit(c)) {
            baseType += c;
        }
    }
    return baseType;
}

// Enhanced Activity-Based Mobility Model
class ActivityBasedMobilityModel {
private:
    std::vector<ActivityLocation> possibleLocations;
    std::map<std::string, std::vector<ActivityLocation>> locationsByType;
    std::map<std::string, std::vector<ActivityLocation>> locationsByBaseType;  // New map for base types
    // ActivityLocation currentLocation;
    std::map<std::string, time_t> lastVisitTime;
    std::random_device rd;
    std::mt19937 gen{rd()};

    void initializeLocations() {
        std::uniform_real_distribution<> dis(0, max_pos);
        
        // Multiple locations for each type
        // std::vector<ActivityLocation> locs = {
        //     {dis(gen), dis(gen), "home", TimeOfDay::NIGHT, 2*hr, 0.9},
        //     {dis(gen), dis(gen), "work", TimeOfDay::MORNING, 2*hr, 0.9},
        //     {100.0, 5.0, "gym1", TimeOfDay::AFTERNOON, 1*hr, 0.4},
        //     {50.0, 140.0, "gym2", TimeOfDay::EVENING, 1*hr, 0.3},
        //     {35.0, 40.0, "coffee1", TimeOfDay::MORNING, 0.5*hr, 0.5},
        //     {120.0, 64.0, "coffee2", TimeOfDay::AFTERNOON, 0.5*hr, 0.3},
        //     {75.0, 162.5, "restaurant1", TimeOfDay::LUNCH, 1*hr, 0.4},
        //     {63.4, 107.0, "restaurant2", TimeOfDay::EVENING, 1*hr, 0.4},
        //     {4.0, 80.0, "leisure1", TimeOfDay::EVENING, 2*hr, 0.6},
        //     {171.0, 100.0, "leisure2", TimeOfDay::EVENING, 2*hr, 0.4}
        // };
        
        std::vector<ActivityLocation> locs = {
            {dis(gen), dis(gen), "home", TimeOfDay::NIGHT, {3*hr, 0.5*hr}, 0.9},
            {dis(gen), dis(gen), "work", TimeOfDay::MORNING, {3*hr, 0.5*hr}, 0.9},
            {100.0, 5.0, "gym1", TimeOfDay::AFTERNOON, {1*hr, 0.2*hr}, 0.4},
            {50.0, 140.0, "gym2", TimeOfDay::EVENING, {1*hr, 0.2*hr}, 0.3},
            {35.0, 40.0, "coffee1", TimeOfDay::MORNING, {0.5*hr, 0.1*hr}, 0.5},
            {120.0, 64.0, "coffee2", TimeOfDay::AFTERNOON, {0.5*hr, 0.1*hr}, 0.3},
            {75.0, 162.5, "restaurant1", TimeOfDay::LUNCH, {1*hr, 0.3*hr}, 0.4},
            {63.4, 107.0, "restaurant2", TimeOfDay::EVENING, {1*hr, 0.3*hr}, 0.4},
            {4.0, 80.0, "leisure1", TimeOfDay::EVENING, {2*hr, 0.5*hr}, 0.6},
            {171.0, 100.0, "leisure2", TimeOfDay::EVENING, {2*hr, 0.5*hr}, 0.4},
            {200.0, 230.0,  "cinema",     TimeOfDay::EVENING, {2.3*hr,   0.2*hr},   0.2},
            {250.0, 10.0,  "park",       TimeOfDay::LUNCH,     {0.5*hr,   0.05*hr}, 0.2},
        };

        possibleLocations = locs;
        
        // Organize by type
        for (const auto& loc : possibleLocations) {
            locationsByType[loc.type].push_back(loc);
            std::string baseType = getBaseType(loc.type);
            locationsByBaseType[baseType].push_back(loc);
        }
    }

public:
    ActivityBasedMobilityModel() {
        initializeLocations();
    }

    ActivityLocation selectNextDestination(TimeOfDay currentTime, 
                                            const ActivityLocation& currentLoc) {
        std::string currentType = currentLoc.type;
        std::string currentBaseType = getBaseType(currentLoc.type);
        std::map<std::string, double> typeWeights;

        // Base weights by time of day
        if (currentTime == TimeOfDay::MORNING) {
            typeWeights = {
                {"work", 0.8}, 
                // {"coffee", 0.3}, 
                // {"gym", 0.1},
                {"home", 0.2}
            };
        } else if (currentTime == TimeOfDay::LUNCH) {
            typeWeights = {
                {"restaurant", 0.6}, 
                {"work", 0.4}//,
                // {"leisure", 0.1},
                // {"park", 0.1}
            };
        } else if (currentTime == TimeOfDay::AFTERNOON) {
            typeWeights = {
                {"work", 0.4}, 
                {"coffee", 0.2},
                {"leisure", 0.4}
            };
        } else if (currentTime == TimeOfDay::EVENING) {
            typeWeights = {
                {"home", 0.3}, 
                {"restaurant", 0.3}, 
                {"leisure", 0.2}, 
                {"gym", 0.1},
                {"cinema", 0.1}
            };
        } else { // NIGHT
            typeWeights = {
                {"home", 0.8}, 
                // {"leisure", 0.2}
            };
        }

        // Reduce probability of selecting the same type
        // if (typeWeights.find(currentType) != typeWeights.end()) {
        //     typeWeights[currentType] = 0.01; // Significantly reduce the weight
        // }
         if (typeWeights.find(currentBaseType) != typeWeights.end()) {
            typeWeights[currentBaseType] = 0.01;
        }

        // Prepare weights and types for the distribution
        std::vector<double> weights;
        std::vector<std::string> types;
        for (const auto& [type, weight] : typeWeights) {
            // if (locationsByType.count(type)) { // Only include available types
            if (locationsByBaseType.count(type)) { // Check base types instead
                weights.push_back(weight);
                types.push_back(type);
            }
        }

        // Log type weights (optional for debugging)
        // m_logger->info("Final type weights:");
        // for (size_t i = 0; i < types.size(); ++i) {
        //     m_logger->info("%s: %f", types[i].c_str(), weights[i]);
        // }

        // Select a location type
        std::discrete_distribution<> dist(weights.begin(), weights.end());
        // std::string selectedType = types[dist(gen)];
        std::string selectedBaseType = types[dist(gen)];

        // Select specific location of the chosen type, avoiding the current location
        // const auto& locations = locationsByType[selectedType];
        const auto& locations = locationsByBaseType[selectedBaseType];
        std::vector<ActivityLocation> filteredLocations;
        for (const auto& loc : locations) {
            // if (loc.type != currentLoc.type) { // Exclude current location
            if (getBaseType(loc.type) != currentBaseType) { // Compare base types
                filteredLocations.push_back(loc);
            }
        }

        // Handle case where no other locations are available
        if (filteredLocations.empty()) {
            return currentLoc; // Return current location if no alternatives exist
        }

        // Create weights based on recent visit times
        std::vector<double> locWeights;
        for (const auto& loc : filteredLocations) {
            // auto lastVisit = lastVisitTime[loc.type];
            auto lastVisit = lastVisitTime[getBaseType(loc.type)];
            double penalty = std::difftime(std::time(nullptr), lastVisit) < 3600 ? 0.1 : 1.0; // Penalize recent visits
            locWeights.push_back(penalty);
        }

        // Select a specific location from filtered options
        std::discrete_distribution<> locDist(locWeights.begin(), locWeights.end());
        ActivityLocation selected = filteredLocations[locDist(gen)];

        // Update the last visit time for the selected location type
        // lastVisitTime[selectedType] = std::time(nullptr);
        lastVisitTime[selectedBaseType] = std::time(nullptr);

        // Log selected type and location (optional for debugging)
        // m_logger->info("Selected type: %s (current type was: %s)", selectedType.c_str(), currentType.c_str());
        // m_logger->info("Selected location: %s", selected.name.c_str());

        return selected;
    }

    double generateDuration(double mean, double stddev, std::mt19937& gen) {
    std::normal_distribution<> distribution(mean, stddev);
    return std::max(0.0, distribution(gen));  // Ensure non-negative duration
    }

    double calculateRealisticSpeed(const std::string& locationType, TimeOfDay currentTime) {
        std::uniform_real_distribution<> speed_dis(min_speed, max_speed);
        double baseSpeed = speed_dis(gen);
        
        // Adjust speed based on location type
        if (locationType.find("work") != std::string::npos) {
            baseSpeed *= 0.7; // slower in work areas
        } else if (locationType.find("leisure") != std::string::npos) {
            baseSpeed *= 0.9; // moderate speed in leisure areas
        }
        
        // Adjust speed based on time of day
        if (currentTime == TimeOfDay::MORNING || currentTime == TimeOfDay::EVENING) {
            baseSpeed *= 0.8; // slower during rush hours
        } else if (currentTime == TimeOfDay::NIGHT) {
            baseSpeed *= 1.2; // faster at night (less traffic)
        }
        
        return baseSpeed;
    }

    bool hasReachedDestination(double currentX, double currentY, 
                              double destX, double destY, 
                              double threshold = 4.0) {
        return calculateDistance(currentX, currentY, destX, destY) < threshold;
    }
};

// Helper function to calculate time of day
TimeOfDay calculateTimeOfDay(uint64_t currentTime) {
    time_t timeInSeconds = currentTime / 1000;
    struct tm* timeInfo = localtime(&timeInSeconds);
    int hour = timeInfo->tm_hour;
    
    if (hour >= 7 && hour < 11) return TimeOfDay::MORNING;
    if (hour >= 11 && hour < 14) return TimeOfDay::LUNCH;
    if (hour >= 14 && hour < 17) return TimeOfDay::AFTERNOON;
    if (hour >= 17 && hour < 24) return TimeOfDay::EVENING;
    return TimeOfDay::NIGHT;
    // int minute = timeInfo->tm_min;  // Use minutes, one day scaled down to one hour
    
    // // Adjust boundaries based on calculated proportional lengths
    // if (minute >= 0 && minute < 10) return TimeOfDay::MORNING;     // Morning
    // if (minute >= 10 && minute < 18) return TimeOfDay::LUNCH;      // Lunch
    // if (minute >= 18 && minute < 26) return TimeOfDay::AFTERNOON;  // Afternoon
    // if (minute >= 26 && minute < 43) return TimeOfDay::EVENING;    // Evening
    // return TimeOfDay::NIGHT;                                      // Night
}

// Global state variables
static ActivityBasedMobilityModel activityModel;
bool atWaypoint = true;
double x_dest, y_dest;
double speed;
double direction;
int pauseTime = 0;
bool Pause = false;
ActivityLocation currentLocation = {Home.x, Home.y, "home", TimeOfDay::MORNING, {3*hr, 0.5*hr}, 0.9};  // Initial location


void RlsUdpTask::onLoop() {
    auto current = utils::CurrentTimeMillis();
    if (current - m_lastLoop > LOOP_PERIOD) {
        m_lastLoop = current;
        heartbeatCycle(current, m_simPos);

        // Handle pause time
        if (Pause && pauseTime > 0) {
            pauseTime--;
            m_logger->info("Paused at location. Time remaining: %d", pauseTime);
            return;
        }

        // Activity-based mobility logic
        if (atWaypoint) {
            Pause = false;
            
            // Get current time of day for context-aware decisions
            TimeOfDay currentTime = calculateTimeOfDay(current);
            
            // Update current location before selecting next
            currentLocation.x = simPos.x;
            currentLocation.y = simPos.y;
            
            // Select next destination based on current time and location
            ActivityLocation nextLocation = activityModel.selectNextDestination(currentTime, currentLocation);
            
            if (nextLocation.type=="home") {
                x_dest = home.x;
                y_dest = home.y;
                currentLocation.type = nextLocation.type;

            } else if (nextLocation.type=="work") {
                x_dest = work.x;
                y_dest = work.y;
                currentLocation.type = nextLocation.type;

            } else {
                x_dest = nextLocation.x;
                y_dest = nextLocation.y;
                currentLocation.type = nextLocation.type;
            }

            
            // Calculate speed considering both location type and time
            speed = activityModel.calculateRealisticSpeed(nextLocation.type, currentTime);
            std::mt19937 gen(std::random_device{}());  // Random number generator

            pauseTime = activityModel.generateDuration(nextLocation.duration.mean, nextLocation.duration.stddev, gen);
            
            // Calculate direction
            double dx = x_dest - simPos.x;
            double dy = y_dest - simPos.y;
            direction = std::atan2(dy, dx);
            
            atWaypoint = false;
            m_logger->info("New destination is %s located at: (%f, %f), speed: %f, time of day: %d", 
                          nextLocation.type.c_str(), x_dest, y_dest, speed, 
                          static_cast<int>(currentTime));
        }
        else {
            // Movement logic
            double dx = x_dest - simPos.x;
            double dy = y_dest - simPos.y;
            double distance = std::sqrt(dx*dx + dy*dy);
            m_logger->info("Distance is: %f", distance);

            if (activityModel.hasReachedDestination(simPos.x, simPos.y, x_dest, y_dest)) {
                simPos.x = x_dest;
                simPos.y = y_dest;
                atWaypoint = true;
                Pause = true;

                // Get current time as string
                auto now = std::chrono::system_clock::now();
                auto time_t_now = std::chrono::system_clock::to_time_t(now);
                std::string timestamp = std::ctime(&time_t_now);
                timestamp.pop_back(); // Remove trailing newline

                // Convert TimeOfDay to string
                TimeOfDay currentTime = calculateTimeOfDay(utils::CurrentTimeMillis());
                std::string timeOfDayStr;
                switch(currentTime) {
                    case TimeOfDay::MORNING: timeOfDayStr = "morning"; break;
                    case TimeOfDay::LUNCH: timeOfDayStr = "lunch"; break;
                    case TimeOfDay::AFTERNOON: timeOfDayStr = "afternoon"; break;
                    case TimeOfDay::EVENING: timeOfDayStr = "evening"; break;
                    case TimeOfDay::NIGHT: timeOfDayStr = "night"; break;
                }

                // Create counter with labels
                std::map<std::string, std::string> labels;
                labels["timestamp"] = timestamp;
                labels["supi"] = m_supi->value;
                labels["location_type"] = currentLocation.type;
                labels["duration"] = std::to_string(pauseTime);
                labels["time_of_day"] = timeOfDayStr;
                auto& counter = destination_visits_family->Add(labels);
                
                // Increment the counter
                counter.Increment();

                m_logger->info("Reached destination: (%f, %f). Pausing for %d time units", 
                              simPos.x, simPos.y, pauseTime);
            }
            else {
                // Smooth movement towards destination
                simPos.x += (speed * dx / distance);
                simPos.y += (speed * dy / distance);
            }
        }

        // Update final positions
        m_simPos.x = (int) simPos.x;
        m_simPos.y = (int) simPos.y;
        m_simPos.z = (int) simPos.z;
    }

    // Network handling (unchanged)
    uint8_t buffer[BUFFER_SIZE];
    InetAddress peerAddress;
    int size = m_server->Receive(buffer, BUFFER_SIZE, RECEIVE_TIMEOUT, peerAddress);
    if (size > 0) {
        auto rlsMsg = rls::DecodeRlsMessage(OctetView{buffer, static_cast<size_t>(size)});
        if (rlsMsg == nullptr)
            m_logger->err("Unable to decode RLS message");
        else
            receiveRlsPdu(peerAddress, std::move(rlsMsg));
    }
}



///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////









void RlsUdpTask::onQuit()
{
    delete m_server;
}

void RlsUdpTask::sendRlsPdu(const InetAddress &addr, const rls::RlsMessage &msg)
{
    OctetString stream;
    rls::EncodeRlsMessage(msg, stream);

    m_server->Send(addr, stream.data(), static_cast<size_t>(stream.length()));
}

void RlsUdpTask::send(int cellId, const rls::RlsMessage &msg)
{
    if (m_cellIdToSti.count(cellId))
    {
        auto sti = m_cellIdToSti[cellId];
        sendRlsPdu(m_cells[sti].address, msg);
    }
}

void RlsUdpTask::receiveRlsPdu(const InetAddress &addr, std::unique_ptr<rls::RlsMessage> &&msg)
{
    if (msg->msgType == rls::EMessageType::HEARTBEAT_ACK)
    {
        if (!m_cells.count(msg->sti))
        {
            m_cells[msg->sti].cellId = ++m_cellIdCounter;
            m_cellIdToSti[m_cells[msg->sti].cellId] = msg->sti;
        }

        int oldDbm = INT32_MIN;
        if (m_cells.count(msg->sti))
            oldDbm = m_cells[msg->sti].dbm;

        m_cells[msg->sti].address = addr;
        m_cells[msg->sti].lastSeen = utils::CurrentTimeMillis();

        int newDbm = ((const rls::RlsHeartBeatAck &)*msg).dbm;
        m_cells[msg->sti].dbm = newDbm;

        if (oldDbm != newDbm)
            onSignalChangeOrLost(m_cells[msg->sti].cellId);
        return;
    }

    if (!m_cells.count(msg->sti))
    {
        // if no HB-ACK received yet, and the message is not HB-ACK, then ignore the message
        return;
    }

    auto w = std::make_unique<NmUeRlsToRls>(NmUeRlsToRls::RECEIVE_RLS_MESSAGE);
    w->cellId = m_cells[msg->sti].cellId;
    w->msg = std::move(msg);
    m_ctlTask->push(std::move(w));
}

void RlsUdpTask::onSignalChangeOrLost(int cellId)
{
    int dbm = INT32_MIN;
    if (m_cellIdToSti.count(cellId))
    {
        auto sti = m_cellIdToSti[cellId];
        dbm = m_cells[sti].dbm;
    }

    auto w = std::make_unique<NmUeRlsToRls>(NmUeRlsToRls::SIGNAL_CHANGED);
    w->cellId = cellId;
    w->dbm = dbm;
    m_ctlTask->push(std::move(w));
}

void RlsUdpTask::heartbeatCycle(uint64_t time, const Vector3 &simPos)
{
    std::set<std::pair<uint64_t, int>> toRemove;

    for (auto &cell : m_cells)
    {
        auto delta = time - cell.second.lastSeen;
        if (delta > HEARTBEAT_THRESHOLD)
            toRemove.insert({cell.first, cell.second.cellId});
    }

    for (auto cell : toRemove)
    {
        m_cells.erase(cell.first);
        m_cellIdToSti.erase(cell.second);
    }

    for (auto cell : toRemove)
        onSignalChangeOrLost(cell.second);

    for (auto &addr : m_searchSpace)
    {
        rls::RlsHeartBeat msg{m_shCtx->sti};
        msg.simPos = simPos;
        sendRlsPdu(addr, msg);
    }
}

void RlsUdpTask::initialize(NtsTask *ctlTask)
{
    m_ctlTask = ctlTask;
}

} // namespace nr::ue
